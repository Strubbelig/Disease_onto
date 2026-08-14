#!/usr/bin/env python3
"""Build and audit the publication release from the single master review CSV.

This script never reads legacy manual-annotation or citation-override tables.
It preserves human review fields, adds explicit derived publication fields,
builds subject-sanitized native hierarchy modules, and generates a compact QA
report used by the review UI and release checklist.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import re
import shutil
import sys
import tarfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from review_extraction_pipeline import (
    CANONICAL_MESH_ONTOLOGY,
    CITATION_REFERENCE_COLUMNS,
    CITATION_REVIEW_COLUMNS,
    CONTROLLED_VALUES,
    DEFINED_BY_REUSE_EXCLUSION_REASON,
    DCTERMS_SOURCE,
    DUPLICATE_MESH_ONTOLOGIES,
    EXACT_MATCH_REUSE_EXCLUSION_REASON,
    IAO_DEFINITION,
    IMPORTED_REUSE_EXCLUSION_REASON,
    OWL_CLASS,
    PUBLICATION_REVIEW_COLUMNS,
    RDF_TYPE,
    REPLACED_CLASS_EXCLUSION_REASON,
    REVIEW_MODULE_BASE_IRI,
    RDFS_COMMENT,
    RDFS_LABEL,
    RDFS_SUBCLASS_OF,
    SCOPE_TERM_EXCLUSION_REASON,
    SKOS_ALT_LABEL,
    SYNDROME_WITH_DISEASE_EXCLUSION_REASON,
    VALUESET_EXCLUSION_REASON,
    PROCESS_CONTEXT_EXCLUSION_REASON,
    ReviewExtractionPipeline,
    ReviewPipelineConfig,
    clean_cell,
    clean_list,
    hierarchy_fetch_ancestors,
    hierarchy_fetch_class,
    hierarchy_fetch_parents,
    hierarchy_triples_for_class,
    join_values,
    native_ontology_group,
    now_iso,
    parse_source_records,
    read_csv_rows,
    safe_name,
    split_semicolon,
    terms_script,
    write_csv_rows,
    write_hierarchy_ttl,
)


EVIDENCE_PREDICATES = {IAO_DEFINITION, RDFS_COMMENT, RDFS_SUBCLASS_OF}
CITATION_CONFIDENCE_VALUES = {
    "manual_verified",
    "metadata_verified",
    "unreviewed",
    "no_candidate",
    "rejected",
}
SUBJECTIVE_COMMENT_PATTERN = re.compile(
    r"\b(terrible|unintelligible|weird|strange|extremely|obviously|clearly|wrong|"
    r"home-made|homemade|stuffed|holding my breath|makes? no sense|nonsensical|"
    r"poorly thought|very narrow|just)\b|\|",
    re.IGNORECASE,
)
WITHDRAWN_IRI_RULE_NOTE = "Unstable local WebProtege IRI provenance."
NEUTRAL_IRI_REVIEW_NOTE = (
    "IRI format is not an exclusion criterion; assess the class's substantive scope, "
    "provenance evidence, annotations, and hierarchy."
)

FINAL_INCLUDED_CODING_COMPLETIONS: dict[str, dict[str, str]] = {
    "http://purl.obolibrary.org/obo/NCIT_C2991": {
        "ontology_type_manual": "curated_ontology",
        "disease_model_category": "no_grounded_model",
        "ontological_category": "no_continuant_occurrent_commitment",
        "reality_vs_classification": "conflated",
    },
    "https://w3id.org/brainteaser/ontology/schema/Condition": {
        "ontological_category": "unclear",
    },
    "http://purl.obolibrary.org/obo/NCIT_C25457": {
        "ontology_type_manual": "curated_ontology",
        "comment_quality": "poor",
        "parentage_quality": "good",
        "entity_quality_score": "1",
    },
    "http://www.case.edu/EpSO.owl#Disease": {
        "ontology_type_manual": "curated_ontology",
        "disease_model_category": "no_grounded_model",
    },
    "http://www.semanticweb.org/rjyy/ontologies/2015/5/ESSO#disease": {
        "ontology_type_manual": "curated_ontology",
        "disease_model_category": "no_grounded_model",
    },
    "http://www.limics.fr/ontologies/ontoDOME#Maladie": {
        "ontology_type_manual": "curated_ontology",
        "disease_model_category": "no_grounded_model",
        "ontological_category": "no_continuant_occurrent_commitment",
        "pathological_grounding": "undefined",
        "reality_vs_classification": "unclear",
        "parentage_quality": "poor",
        "entity_quality_score": "1",
    },
    "http://purl.obolibrary.org/obo/IEV_0000075": {
        "ontology_type_manual": "curated_ontology",
        "disease_model_category": "entity_as_process",
        "ontological_category": "occurrent",
        "pathological_grounding": "undefined",
        "reality_vs_classification": "biological_state",
        "parentage_quality": "good",
        "entity_quality_score": "1",
    },
    "http://purl.obolibrary.org/obo/NCIT_C28193": {
        "ontology_type_manual": "curated_ontology",
        "ontological_category": "no_continuant_occurrent_commitment",
        "parentage_quality": "poor",
        "entity_quality_score": "1",
    },
}


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalise_key(value: str) -> str:
    return terms_script.normalise_ontology_id_for_dependency(value or "")


def prefixed_source_ids(value: str) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for part in split_semicolon(value):
        if ":" in part:
            source, ontology = part.split(":", 1)
            pairs.append((source.strip(), ontology.strip()))
    return pairs


def iri_namespace(iri: str) -> str:
    if "#" in iri:
        return iri.rsplit("#", 1)[0] + "#"
    if "/obo/" in iri and re.search(r"/obo/[A-Za-z][A-Za-z0-9-]*_", iri):
        return re.sub(r"_[^/]+$", "_", iri)
    return iri.rsplit("/", 1)[0] + "/" if "/" in iri else iri


def inferred_key_for_iri(iri: str) -> str:
    return normalise_key(terms_script.infer_native_ontology_guess(iri))


def json_values(row: dict[str, str], json_field: str, legacy_field: str, *, split: bool) -> list[str]:
    raw = clean_cell(row.get(json_field, ""))
    if raw:
        try:
            values = json.loads(raw)
            if isinstance(values, list):
                return [clean_cell(value) for value in values if clean_cell(value)]
        except json.JSONDecodeError:
            pass
    legacy = clean_cell(row.get(legacy_field, ""))
    if not legacy:
        return []
    return split_semicolon(legacy) if split else [legacy]


class PublicationReadiness:
    def __init__(self, config: ReviewPipelineConfig | None = None) -> None:
        self.config = config or ReviewPipelineConfig()
        self.pipeline = ReviewExtractionPipeline(self.config)
        self.review_dir = self.config.table_dir.parent
        self.release_dir = self.review_dir / "Publication release"
        self.audit_dir = self.release_dir / "audit"
        self.report_json = self.audit_dir / "publication_readiness_report.json"
        self.report_md = self.audit_dir / "publication_readiness_report.md"
        self.changelog = self.audit_dir / "publication_changes.json"
        self._changes: list[dict[str, str]] = []

    def _record_change(self, row: dict[str, str], field: str, old: str, new: str, reason: str) -> None:
        if clean_cell(old) == clean_cell(new):
            return
        self._changes.append(
            {
                "class_iri": row.get("class_iri", ""),
                "ontology": native_ontology_group(row),
                "field": field,
                "old": clean_cell(old),
                "new": clean_cell(new),
                "reason": reason,
            }
        )
        row[field] = new

    def baseline(self) -> Path:
        stamp = utc_stamp()
        target_dir = self.audit_dir / f"baseline_{stamp}"
        target_dir.mkdir(parents=True, exist_ok=True)
        archive = target_dir / "pre_remediation_snapshot.tar.gz"
        paths = [
            self.config.enriched_csv,
            Path(__file__),
            self.config.review_core_ttl,
            self.config.review_ontology_ttl,
            self.review_dir / "Python scripts" / "review_extraction_pipeline.py",
            self.review_dir / "Python scripts" / "prefill_manual_annotations.py",
            self.review_dir / "Workflow instructions" / "entity_quality_assessment_workflow.md",
            self.review_dir / "Workflow instructions" / "Reporting_Guideline_Applicability.md",
            self.review_dir / "Disease_Ontology_Artifact_Evaluation_Manuscript.md",
            self.review_dir / "Disease_Ontology_Artifact_Evaluation_Manuscript.docx",
        ]
        with tarfile.open(archive, "w:gz") as tar:
            for path in paths:
                if path.exists():
                    tar.add(path, arcname=str(path.relative_to(self.review_dir.parent)))
        manifest = {
            "created_at": now_iso(),
            "archive": str(archive),
            "archive_sha256": sha256(archive),
            "files": [
                {"path": str(path), "sha256": sha256(path)}
                for path in paths
                if path.exists()
            ],
        }
        (target_dir / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return archive

    def _source_module_candidates(self, row: dict[str, str], native_key: str) -> list[tuple[str, Path]]:
        candidates: list[tuple[str, Path]] = []
        pairs = prefixed_source_ids(row.get("native_source_ontology_ids", ""))
        if not pairs:
            for record in parse_source_records(row):
                ontology = clean_cell(record.get("ontology", ""))
                if ontology and normalise_key(ontology) == native_key:
                    pairs.append((clean_cell(record.get("source", "")), ontology))
        if not pairs:
            pairs.append(("BioPortal", native_ontology_group(row)))

        for source, ontology in pairs:
            key = safe_name(ontology)
            source_cf = source.casefold()
            if source_cf == "bioportal":
                candidates.append((f"BioPortal:{ontology}", self.config.bioportal_module_dir / f"{key}_hierarchy.ttl"))
            elif source_cf == "ols":
                candidates.append((f"OLS:{ontology}", self.config.ols_module_dir / f"{key}_ols_hierarchy.ttl"))
            elif source_cf == "obo foundry direct":
                candidates.append((f"OBO:{ontology}", self.config.obo_module_dir / f"{key}_obo_direct_hierarchy.ttl"))

        plain_key = safe_name(native_ontology_group(row))
        candidates.extend(
            [
                (f"BioPortal:{plain_key}", self.config.bioportal_module_dir / f"{plain_key}_hierarchy.ttl"),
                (f"OLS:{plain_key}", self.config.ols_module_dir / f"{plain_key}_ols_hierarchy.ttl"),
                (f"OBO:{plain_key}", self.config.obo_module_dir / f"{plain_key}_obo_direct_hierarchy.ttl"),
            ]
        )
        seen: set[Path] = set()
        return [(label, path) for label, path in candidates if not (path in seen or seen.add(path))]

    def _fetch_bioportal_target(self, ontology: str, iri: str) -> set[tuple[str, str, str, bool]]:
        try:
            apikey = terms_script.load_bioportal_api_key()
        except SystemExit:
            return set()
        cache_dir = self.config.hierarchy_cache_dir / "publication-native" / safe_name(ontology)
        target = hierarchy_fetch_class(ontology, iri, apikey, cache_dir)
        if not target.get("@id"):
            return set()
        nodes: dict[str, dict[str, Any]] = {target["@id"]: target}
        for ancestor in hierarchy_fetch_ancestors(ontology, iri, apikey, cache_dir):
            if ancestor.get("@id"):
                nodes[ancestor["@id"]] = ancestor
        triples: set[tuple[str, str, str, bool]] = set()
        for record in nodes.values():
            triples.update(hierarchy_triples_for_class(record))
        for child_iri in sorted(nodes):
            for parent in hierarchy_fetch_parents(ontology, child_iri, apikey, cache_dir):
                parent_iri = clean_cell(parent.get("@id", ""))
                if parent_iri and parent_iri in nodes:
                    triples.add((child_iri, RDFS_SUBCLASS_OF, parent_iri, True))
        triples.add((iri, DCTERMS_SOURCE, f"Native BioPortal hierarchy: {ontology}", False))
        return triples

    def _fallback_triples(self, row: dict[str, str]) -> set[tuple[str, str, str, bool]]:
        iri = row.get("class_iri", "")
        triples: set[tuple[str, str, str, bool]] = {(iri, RDF_TYPE, OWL_CLASS, True)}
        label = clean_cell(row.get("preferred_label", ""))
        if label:
            triples.add((iri, RDFS_LABEL, label, False))
        for value in json_values(row, "definition_values_json", "definition", split=False):
            triples.add((iri, IAO_DEFINITION, value, False))
        for value in json_values(row, "comment_values_json", "comments", split=False):
            triples.add((iri, RDFS_COMMENT, value, False))
        for value in json_values(row, "synonym_values_json", "synonyms", split=True):
            triples.add((iri, SKOS_ALT_LABEL, value, False))
        parent_iris = json_values(row, "parent_iri_values_json", "parent_iris", split=True)
        parent_labels = json_values(row, "parent_label_values_json", "parent_labels", split=True)
        for index, parent_iri in enumerate(parent_iris):
            triples.add((iri, RDFS_SUBCLASS_OF, parent_iri, True))
            triples.add((parent_iri, RDF_TYPE, OWL_CLASS, True))
            if index < len(parent_labels) and parent_labels[index]:
                triples.add((parent_iri, RDFS_LABEL, parent_labels[index], False))
        triples.add((iri, DCTERMS_SOURCE, "Fallback evidence copied losslessly from the master review CSV", False))
        return triples

    def _sanitize_module_triples(
        self,
        native_key: str,
        target_iris: set[str],
        triples: set[tuple[str, str, str, bool]],
    ) -> set[tuple[str, str, str, bool]]:
        target_namespaces = {iri_namespace(iri) for iri in target_iris}

        def local_subject(subject: str) -> bool:
            if subject in target_iris:
                return True
            inferred = inferred_key_for_iri(subject)
            if inferred:
                return inferred == native_key
            return iri_namespace(subject) in target_namespaces

        sanitized: set[tuple[str, str, str, bool]] = set()
        referenced_parents: set[str] = set()
        labels: dict[str, set[str]] = defaultdict(set)
        for subject, predicate, obj, object_is_iri in triples:
            if predicate == RDFS_LABEL and not object_is_iri:
                labels[subject].add(obj)
            if not local_subject(subject):
                continue
            sanitized.add((subject, predicate, obj, object_is_iri))
            if predicate == RDFS_SUBCLASS_OF and object_is_iri:
                referenced_parents.add(obj)

        for parent in referenced_parents:
            sanitized.add((parent, RDF_TYPE, OWL_CLASS, True))
            for label in labels.get(parent, set()):
                sanitized.add((parent, RDFS_LABEL, label, False))
        return sanitized

    def build_native_modules(self, *, allow_network: bool = True) -> list[dict[str, Any]]:
        rows = read_csv_rows(self.config.enriched_csv)
        groups: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in rows:
            key = normalise_key(native_ontology_group(row)) or safe_name(row.get("ontology", "unknown"))
            groups[key].append(row)

        self.config.native_module_dir.mkdir(parents=True, exist_ok=True)
        cached_generated_modules: dict[str, set[tuple[str, str, str, bool]]] = {}
        for stale_path in self.config.native_module_dir.glob("*_native_hierarchy.ttl"):
            if not allow_network:
                cached_generated_modules[stale_path.name] = set(
                    self.pipeline._parse_simple_ttl_triples(stale_path.read_text(encoding="utf-8"))
                )
            stale_path.unlink()
        manifest: list[dict[str, Any]] = []
        status_by_iri: dict[str, dict[str, str]] = {}
        for index, (native_key, group_rows) in enumerate(sorted(groups.items()), start=1):
            target_iris = {row["class_iri"] for row in group_rows if row.get("class_iri")}
            raw_triples: set[tuple[str, str, str, bool]] = set()
            source_labels: list[str] = []
            source_covered: set[str] = set()
            module_filename = f"{safe_name(native_key)}_native_hierarchy.ttl"
            cached_triples = cached_generated_modules.get(module_filename, set())
            if cached_triples:
                raw_triples.update(cached_triples)
                for row in group_rows:
                    if row.get("hierarchy_evidence_status") == "native_module":
                        source_covered.add(row.get("class_iri", ""))
                    cached_source = clean_cell(row.get("hierarchy_module_source", ""))
                    if cached_source:
                        source_labels.extend(
                            part.strip()
                            for part in cached_source.split(";")
                            if part.strip()
                        )
            for row in group_rows:
                iri = row.get("class_iri", "")
                for source_label, path in self._source_module_candidates(row, native_key):
                    if not path.exists():
                        continue
                    text = path.read_text(encoding="utf-8", errors="ignore")
                    if f"<{iri}>" not in text:
                        continue
                    parsed = set(self.pipeline._parse_simple_ttl_triples(text))
                    raw_triples.update(parsed)
                    source_labels.append(f"{source_label} ({path.name})")
                    source_covered.add(iri)
                    break

            if allow_network:
                for row in group_rows:
                    iri = row.get("class_iri", "")
                    if not iri or iri in source_covered:
                        continue
                    bp_ids = [
                        ontology
                        for source, ontology in prefixed_source_ids(row.get("native_source_ontology_ids", ""))
                        if source.casefold() == "bioportal"
                    ]
                    if not bp_ids:
                        bp_ids = [
                            clean_cell(record.get("ontology", ""))
                            for record in parse_source_records(row)
                            if clean_cell(record.get("source", "")).casefold() == "bioportal"
                            and normalise_key(clean_cell(record.get("ontology", ""))) == native_key
                        ]
                    for ontology in bp_ids[:1]:
                        fetched = self._fetch_bioportal_target(ontology, iri)
                        if fetched:
                            raw_triples.update(fetched)
                            source_labels.append(f"BioPortal API:{ontology}")
                            source_covered.add(iri)
                            break

            for row in group_rows:
                iri = row.get("class_iri", "")
                if iri not in source_covered:
                    raw_triples.update(self._fallback_triples(row))

            sanitized = self._sanitize_module_triples(native_key, target_iris, raw_triples)
            module_path = self.config.native_module_dir / module_filename
            module_iri = REVIEW_MODULE_BASE_IRI + safe_name(native_key)
            write_hierarchy_ttl(
                module_path,
                module_iri,
                sanitized,
                source_label="; ".join(dict.fromkeys(source_labels)) or "Master CSV fallback evidence",
                ontology_versions=join_values(row.get("ontology_versions", "") for row in group_rows),
                retrieved_at=now_iso(),
            )

            per_status = Counter()
            for row in group_rows:
                iri = row.get("class_iri", "")
                target_triples = [triple for triple in sanitized if triple[0] == iri]
                evidence = any(triple[1] in EVIDENCE_PREDICATES for triple in target_triples)
                if iri in source_covered:
                    status = "native_module"
                    detail = "Native source module or native registry API evidence."
                elif evidence:
                    status = "fallback_with_evidence"
                    detail = "Native registry module unavailable; retained source evidence from the master CSV."
                else:
                    status = "insufficient_metadata"
                    detail = "No native definition, comment, or asserted superclass could be recovered."
                per_status[status] += 1
                status_by_iri[iri] = {
                    "hierarchy_evidence_status": status,
                    "hierarchy_module_iri": module_iri,
                    "hierarchy_module_source": "; ".join(dict.fromkeys(source_labels)) or "master_csv_fallback",
                    "hierarchy_evidence_detail": detail,
                }

            manifest.append(
                {
                    "native_ontology": native_key.upper(),
                    "module_iri": module_iri,
                    "module_path": str(module_path.relative_to(self.review_dir)),
                    "target_count": len(target_iris),
                    "target_iris": sorted(target_iris),
                    "source_labels": list(dict.fromkeys(source_labels)),
                    "evidence_status_counts": dict(per_status),
                    "triple_count": len(sanitized),
                }
            )
            print(f"[{index}/{len(groups)}] {native_key}: {len(target_iris)} targets -> {module_path.name}")

        for row in rows:
            for field, value in status_by_iri.get(row.get("class_iri", ""), {}).items():
                row[field] = value
        self.pipeline._write_master_review_rows(rows)
        self.config.native_module_manifest.write_text(
            json.dumps({"generated_at": now_iso(), "modules": manifest}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return manifest

    def _automated_exclusion_context(self, rows: list[dict[str, str]]) -> dict[str, Any]:
        prefiltered = [
            row for row in rows
            if row.get("ontology", "").upper() not in DUPLICATE_MESH_ONTOLOGIES
            and not self.pipeline._is_excluded_scope_term_row(row)
            and not self.pipeline._is_replaced_class_row(row)
            and not self.pipeline._is_excluded_valueset_row(row)
        ]
        disease_sources = self.pipeline._disease_source_ontology_ids(prefiltered)
        without_syndromes = [
            row for row in prefiltered
            if not self.pipeline._is_syndrome_redundant_when_disease_present(row, disease_sources)
        ]
        disease_root_sources = self.pipeline._disease_root_source_ontology_ids(without_syndromes)
        return {
            "disease_sources": disease_sources,
            "disease_root_sources": disease_root_sources,
        }

    def _automated_exclusion_reason(self, row: dict[str, str], context: dict[str, Any]) -> tuple[str, str]:
        if row.get("ontology", "").upper() in DUPLICATE_MESH_ONTOLOGIES:
            return "duplicate_registry_mirror", f"Duplicate MeSH mirror; canonical source is {CANONICAL_MESH_ONTOLOGY}."
        if self.pipeline._is_excluded_scope_term_row(row):
            return SCOPE_TERM_EXCLUSION_REASON, "Search term is outside the disease-model synthesis scope."
        if self.pipeline._is_replaced_class_row(row):
            return REPLACED_CLASS_EXCLUSION_REASON, "A stronger native representative class is reviewed for this ontology."
        if self.pipeline._is_excluded_valueset_row(row):
            return VALUESET_EXCLUSION_REASON, "Value-set collection rather than an independent ontology model."
        if self.pipeline._is_syndrome_redundant_when_disease_present(row, context["disease_sources"]):
            return SYNDROME_WITH_DISEASE_EXCLUSION_REASON, "Disease representative already selected from the same source."
        if self.pipeline._is_process_context_row(row, context["disease_root_sources"]):
            return PROCESS_CONTEXT_EXCLUSION_REASON, "Disease representative already selected; process context is not reviewed separately."
        if self.pipeline._is_exact_match_reuse_row(row):
            return EXACT_MATCH_REUSE_EXCLUSION_REASON, "Exact match to a canonical external disease model."
        native_guess = row.get("native_ontology_guess") or terms_script.infer_native_ontology_guess(row.get("class_iri", ""))
        if self.pipeline._defined_by_external_targets(row, native_guess):
            return DEFINED_BY_REUSE_EXCLUSION_REASON, "Defined by an external class and not an independent implementation."
        if row.get("native_term_status") == "likely_imported_or_reused_term":
            return IMPORTED_REUSE_EXCLUSION_REASON, "Imported or reused term rather than an independent native implementation."
        return "", ""

    @staticmethod
    def _quality_presence(triples: list[tuple[str, str, str, bool]], iri: str) -> tuple[bool, bool, bool]:
        has_definition = any(s == iri and p == IAO_DEFINITION and not is_iri and clean_cell(o) for s, p, o, is_iri in triples)
        has_comment = any(s == iri and p == RDFS_COMMENT and not is_iri and clean_cell(o) for s, p, o, is_iri in triples)
        has_parent = any(s == iri and p == RDFS_SUBCLASS_OF and is_iri for s, p, o, is_iri in triples)
        return has_definition, has_comment, has_parent

    @staticmethod
    def _neutral_comment_proposal(text: str) -> str:
        proposed = clean_cell(text)
        proposed = re.sub(
            r"\bMany strange most probably Protege generated error classes\b",
            "The ontology contains many probable Protege-generated error classes",
            proposed,
            flags=re.IGNORECASE,
        )
        proposed = re.sub(
            r"\b(?:very )?strange hiera(?:r)?chy of ([^.]+)\.",
            r"The hierarchy of \1 is internally inconsistent.",
            proposed,
            flags=re.IGNORECASE,
        )
        proposed = re.sub(
            r"\bStrange is_a hierarchy with ([^.]+)\.",
            r"The is-a hierarchy is unusual: \1.",
            proposed,
            flags=re.IGNORECASE,
        )
        replacements = [
            (r"\bTerrible wording\b", "The wording is difficult to interpret"),
            (r"\bunintelligible\b", "not readily interpretable"),
            (r"\bExtremely strange setup\b", "The modelling structure is unusual"),
            (r"\bStrangely,?\s*", ""),
            (r"\bstrangely placed\b", "incongruously placed"),
            (r"\bstrange\b", "unusual"),
            (r"\bweird\b", "unconventional"),
            (r"\bobviously\b", ""),
            (r"\bclearly\b", ""),
            (r"\bhome-made\b", "locally defined"),
            (r"\bhomemade\b", "locally defined"),
            (r"\bstuffed codes\b", "embedded codes"),
            (r"\bmakes? no sense\b", "is not semantically coherent"),
            (r"\bnonsensical\b", "semantically incoherent"),
            (r"\bwrong subsumption\b", "incorrect subsumption"),
            (r"\bwrong is[- ]a\b", "incorrect is-a"),
            (r"\bwrong superclass\b", "inappropriate superclass"),
            (r"\ba very narrow\b", "an application-specific"),
            (r"\bvery narrow\b", "application-specific"),
            (r"\bAgain just three different definitions copy pasted\b", "The annotation combines three source definitions without reconciliation"),
            (r"\bcopy pasted\b", "copied without reconciliation"),
            (r"\bmost probably\b", "probably"),
            (r"\bHolding my breath[^.]*\.?", ""),
        ]
        for pattern, replacement in replacements:
            proposed = re.sub(pattern, replacement, proposed, flags=re.IGNORECASE)
        proposed = re.sub(r"\s*\|\s*", ". ", proposed)
        proposed = re.sub(r"\ba application-specific\b", "an application-specific", proposed, flags=re.IGNORECASE)
        proposed = re.sub(r"\ba incorrect\b", "an incorrect", proposed, flags=re.IGNORECASE)
        proposed = re.sub(r"\bowl:thng\b", "owl:Thing", proposed, flags=re.IGNORECASE)
        proposed = re.sub(r"\bopenare:", "opencare:", proposed, flags=re.IGNORECASE)
        proposed = re.sub(r"\bhierachy\b", "hierarchy", proposed, flags=re.IGNORECASE)
        proposed = re.sub(r"\bprotege generated\b", "Protege-generated", proposed, flags=re.IGNORECASE)
        proposed = re.sub(
            r"The ontology contains many probable Protege-generated error classes in the ontology",
            "The ontology contains many probable Protege-generated error classes",
            proposed,
            flags=re.IGNORECASE,
        )
        proposed = re.sub(r"\b(can't|cannot not)\b", "cannot", proposed, flags=re.IGNORECASE)
        proposed = re.sub(r"\bisn't\b", "is not", proposed, flags=re.IGNORECASE)
        proposed = re.sub(r"\bdoesn't\b", "does not", proposed, flags=re.IGNORECASE)
        proposed = re.sub(r"\.\s*,\s*", ". ", proposed)
        proposed = re.sub(r"\.{2,}", ".", proposed)
        proposed = re.sub(r"\s+([,.;:])", r"\1", proposed)
        proposed = re.sub(r"\s{2,}", " ", proposed).strip(" |")
        proposed = re.sub(
            r"(^|[.!?]\s+)([a-z])",
            lambda match: match.group(1) + match.group(2).upper(),
            proposed,
        )
        if proposed:
            proposed = proposed[0].upper() + proposed[1:]
            if proposed[-1] not in ".!?":
                proposed += "."
        return proposed

    def _normalise_citation_row(self, row: dict[str, str]) -> None:
        status = clean_cell(row.get("modelling_citation_status", "")).lower()
        approved = clean_cell(row.get("modelling_citation_approved", "")).lower()
        confidence = clean_cell(row.get("modelling_citation_confidence", ""))
        payload = any(clean_cell(row.get(field, "")) for field in CITATION_REFERENCE_COLUMNS)

        for field, replacement in {
            "modelling_citation_source": "master CSV (legacy citation record consolidated)",
            "modelling_citation_lookup_source": "legacy citation lookup consolidated into master CSV",
        }.items():
            old = clean_cell(row.get(field, ""))
            if "citation_link_preview.csv" in old:
                self._record_change(
                    row,
                    field,
                    old,
                    replacement,
                    "Removed a reference to the deleted legacy citation table; provenance now names the consolidated master record.",
                )

        if status == "no_citation" and approved == "yes":
            self._record_change(
                row,
                "modelling_citation_approved",
                approved,
                "none",
                "A no-citation state cannot simultaneously be approved as a citation.",
            )
            approved = "none"

        if confidence and confidence not in CITATION_CONFIDENCE_VALUES:
            if confidence.casefold() not in {"correct", "high", "medium", "low_screen", "no_candidate"}:
                note = clean_cell(row.get("modelling_citation_notes", ""))
                if confidence not in note:
                    self._record_change(
                        row,
                        "modelling_citation_notes",
                        note,
                        "; ".join(filter(None, [note, confidence])),
                        "Moved free-text citation note out of the controlled confidence field.",
                    )

        if approved == "yes" and payload:
            normalized_confidence = "manual_verified"
        elif approved == "no":
            normalized_confidence = "rejected"
        elif status == "no_citation" or approved == "none":
            normalized_confidence = "no_candidate"
        elif payload:
            normalized_confidence = "unreviewed"
        else:
            normalized_confidence = "unreviewed"
        self._record_change(
            row,
            "modelling_citation_confidence",
            confidence,
            normalized_confidence,
            "Normalized citation confidence to the publication controlled vocabulary.",
        )

        if approved in {"no", "none"} or status == "no_citation":
            for field in CITATION_REFERENCE_COLUMNS:
                if row.get(field):
                    self._record_change(
                        row,
                        field,
                        row.get(field, ""),
                        "",
                        "Rejected/no-citation records must not retain citation payload.",
                    )
            row["modelling_citation_status"] = "no_citation"

    def _apply_curated_citation_fixes(self, rows: list[dict[str, str]]) -> None:
        fixes = {
            "abd": {
                "modelling_citation_status": "cited",
                "modelling_citation_confidence": "metadata_verified",
                "modelling_citation_doi": "10.48550/arXiv.1609.05774",
                "modelling_citation_url": "https://doi.org/10.48550/arXiv.1609.05774",
                "modelling_citation_publication_title": "A globally-applicable disease ontology for biosurveillance; Anthology of Biosurveillance Diseases (ABD)",
                "modelling_citation_authors": "A.R. Daughton; R. Priedhorsky; G. Fairchild; N. Generous; A. Hengartner; E. Abeyta; N. Velappan; A. Lillo; K. Stark; A. Deshpande",
                "modelling_citation_year": "2016",
                "modelling_citation_venue": "arXiv",
                "modelling_citation_lookup_source": "arXiv",
                "modelling_citation_assignment_flag": "ok",
                "modelling_citation_assignment_flag_reason": "The arXiv record explicitly presents the Anthology of Biosurveillance Diseases (ABD).",
            },
            "ad_cdo": {
                "modelling_citation_status": "cited",
                "modelling_citation_confidence": "metadata_verified",
                "modelling_citation_doi": "10.5281/zenodo.20510832",
                "modelling_citation_url": "https://doi.org/10.5281/zenodo.20510832",
                "modelling_citation_publication_title": "Alzheimer's Disease Common Data Element Ontology for Clinical Trials (AD-CDO)",
                "modelling_citation_authors": "Zenan Sun; Rashmie Abeysinghe; Xiaojin Li; Xinyue Hu; Qizhen Lan; Lijing Zhu; Licong Cui; Guo-Qiang Zhang; Jiang Bian; Cui Tao",
                "modelling_citation_year": "2026",
                "modelling_citation_venue": "Zenodo",
                "modelling_citation_lookup_source": "Zenodo",
                "modelling_citation_assignment_flag": "ok",
                "modelling_citation_assignment_flag_reason": "The Zenodo record is the AD-CDO ontology release.",
            },
            "dmdsont": {
                "modelling_citation_status": "cited",
                "modelling_citation_confidence": "metadata_verified",
                "modelling_citation_doi": "10.6084/m9.figshare.21070348.v1",
                "modelling_citation_url": "https://doi.org/10.6084/m9.figshare.21070348.v1",
                "modelling_citation_publication_title": "Diabetes Mellitus Diagnosis and Support Ontology (DMDSOnt)",
                "modelling_citation_authors": "Duygu Celik Ertugrul; Yiltan Bitirim",
                "modelling_citation_year": "2022",
                "modelling_citation_venue": "Figshare",
                "modelling_citation_lookup_source": "Figshare",
                "modelling_citation_assignment_flag": "ok",
                "modelling_citation_assignment_flag_reason": "The Figshare record is the DMDSOnt ontology release.",
            },
            "ogms": {
                "modelling_citation_status": "cited",
                "modelling_citation_confidence": "manual_verified",
                "modelling_citation_publication_title": "Toward an ontological treatment of disease and diagnosis",
                "modelling_citation_authors": "Scheuermann RH; Ceusters W; Smith B",
                "modelling_citation_year": "2009",
                "modelling_citation_venue": "AMIA Summit on Translational Bioinformatics Proceedings",
                "modelling_citation_bibliographic_citation": "Scheuermann RH; Ceusters W; Smith B (2009) Toward an ontological treatment of disease and diagnosis. AMIA Summit on Translational Bioinformatics Proceedings:116-120.",
            },
            "hino": {
                "modelling_citation_status": "cited",
                "modelling_citation_confidence": "manual_verified",
                "modelling_citation_doi": "10.48550/arXiv.1311.3355",
                "modelling_citation_publication_title": "HINO: a BFO-aligned ontology representing human molecular interactions and pathways",
                "modelling_citation_authors": "Xiang Z; He Y",
                "modelling_citation_year": "2013",
                "modelling_citation_venue": "arXiv",
                "modelling_citation_url": "https://doi.org/10.48550/arXiv.1311.3355",
            },
            "sio": {
                "modelling_citation_source_ontology_id": "SIO",
                "modelling_citation_status": "cited",
                "modelling_citation_confidence": "metadata_verified",
                "modelling_citation_doi": "10.1186/2041-1480-5-14",
                "modelling_citation_pmid": "24602174",
                "modelling_citation_pmcid": "PMC4015691",
                "modelling_citation_url": "https://doi.org/10.1186/2041-1480-5-14",
                "modelling_citation_publication_title": "The Semanticscience Integrated Ontology (SIO) for biomedical research and knowledge discovery",
                "modelling_citation_authors": "Dumontier M; Baker CJO; Baran J; Callahan A; Chepelev L; Cruz-Toledo J; Del Rio NR; Duck G; Furlong LI; Keath N; Klassen D; McCusker JP; Queralt-Rosinach N; Samwald M; Villanueva-Rosales N; Wilkinson MD; Hoehndorf R",
                "modelling_citation_year": "2014",
                "modelling_citation_venue": "Journal of Biomedical Semantics, 5:14",
                "modelling_citation_bibliographic_citation": "Dumontier M et al. (2014) The Semanticscience Integrated Ontology (SIO) for biomedical research and knowledge discovery. Journal of Biomedical Semantics 5:14. doi:10.1186/2041-1480-5-14. PMID:24602174; PMCID:PMC4015691.",
                "modelling_citation_lookup_source": "PubMed/PMC",
                "modelling_citation_approved": "yes",
                "modelling_citation_assignment_flag": "ok",
                "modelling_citation_assignment_flag_reason": "The publication explicitly presents the Semanticscience Integrated Ontology.",
            },
        }
        for row in rows:
            native_key = normalise_key(row.get("native_ontology_guess", "") or native_ontology_group(row))
            citation_key = normalise_key(row.get("modelling_citation_source_ontology_id", ""))
            key = native_key if native_key in fixes else citation_key
            fix = fixes.get(key)
            if not fix:
                continue
            for field, value in fix.items():
                if value and clean_cell(row.get(field, "")) != value:
                    self._record_change(row, field, row.get(field, ""), value, "Curated publication metadata correction.")

    def _crossref_metadata(self, doi: str) -> dict[str, str]:
        doi = doi.strip().removeprefix("https://doi.org/").removeprefix("http://doi.org/")
        if not doi:
            return {}
        try:
            response = requests.get(
                f"https://api.crossref.org/works/{requests.utils.quote(doi, safe='')}",
                headers={"User-Agent": "disease-ontology-review/1.0 (mailto:ontology-review@example.org)"},
                timeout=30,
            )
            response.raise_for_status()
            message = response.json().get("message", {})
        except Exception:
            return {}
        authors = []
        for author in message.get("author", []) or []:
            name = " ".join(filter(None, [clean_cell(author.get("given", "")), clean_cell(author.get("family", ""))]))
            if name:
                authors.append(name)
        issued = message.get("issued", {}).get("date-parts", [[]])
        year = str(issued[0][0]) if issued and issued[0] else ""
        return {
            "modelling_citation_publication_title": clean_cell((message.get("title") or [""])[0]),
            "modelling_citation_authors": "; ".join(authors),
            "modelling_citation_year": year,
            "modelling_citation_venue": clean_cell((message.get("container-title") or [""])[0])
            or clean_cell(message.get("publisher", "")),
            "modelling_citation_url": f"https://doi.org/{doi}",
        }

    def _propagate_ontology_level_citations(self, rows: list[dict[str, str]]) -> None:
        """Fill blank sibling rows from one unambiguous ontology-level decision."""
        bibliographic_fields = [
            "modelling_citation_doi",
            "modelling_citation_pmid",
            "modelling_citation_pmcid",
            "modelling_citation_url",
            "modelling_citation_publication_title",
            "modelling_citation_authors",
            "modelling_citation_year",
            "modelling_citation_venue",
            "modelling_citation_bibliographic_citation",
        ]
        groups: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in rows:
            key = normalise_key(
                row.get("modelling_citation_source_ontology_id", "")
                or row.get("native_ontology_guess", "")
                or row.get("ontology", "")
            )
            if key:
                groups[key].append(row)

        copy_fields = list(
            dict.fromkeys(
                CITATION_REFERENCE_COLUMNS
                + [
                    "modelling_citation_source_ontology_id",
                    "modelling_citation_status",
                    "modelling_citation_confidence",
                    "modelling_citation_approved",
                    "modelling_citation_assignment_flag",
                    "modelling_citation_assignment_flag_reason",
                    "modelling_citation_assignment_checked_at",
                    "modelling_citation_notes",
                ]
            )
        )
        for group_rows in groups.values():
            approved_templates = [
                row
                for row in group_rows
                if clean_cell(row.get("modelling_citation_approved", "")).lower() == "yes"
                and any(clean_cell(row.get(field, "")) for field in bibliographic_fields)
            ]
            absent_templates = [
                row
                for row in group_rows
                if clean_cell(row.get("modelling_citation_approved", "")).lower() in {"none", "no"}
                and clean_cell(row.get("modelling_citation_status", "")).lower() == "no_citation"
            ]
            if approved_templates and absent_templates:
                continue
            template = approved_templates[0] if approved_templates else (absent_templates[0] if absent_templates else None)
            if not template:
                continue
            for row in group_rows:
                if clean_cell(row.get("modelling_citation_approved", "")):
                    continue
                if any(clean_cell(row.get(field, "")) for field in bibliographic_fields):
                    continue
                for field in copy_fields:
                    value = template.get(field, "")
                    if clean_cell(row.get(field, "")) != value:
                        self._record_change(
                            row,
                            field,
                            row.get(field, ""),
                            value,
                            "Propagated an unambiguous ontology-level citation decision to a sibling class.",
                        )

    def enrich_citations(self) -> None:
        rows = read_csv_rows(self.config.enriched_csv)
        self._changes = []
        self._apply_curated_citation_fixes(rows)
        self._propagate_ontology_level_citations(rows)
        metadata_by_doi: dict[str, dict[str, str]] = {}
        for row in rows:
            self._normalise_citation_row(row)
            if clean_cell(row.get("modelling_citation_approved", "")).lower() != "yes":
                continue
            doi = clean_cell(row.get("modelling_citation_doi", ""))
            if not doi:
                continue
            metadata = metadata_by_doi.setdefault(doi, self._crossref_metadata(doi))
            for field, value in metadata.items():
                if value and not clean_cell(row.get(field, "")):
                    self._record_change(row, field, "", value, "Filled approved citation metadata from Crossref.")
            if not row.get("modelling_citation_bibliographic_citation"):
                formatted = self.pipeline._format_bibliographic_citation(row, doi=doi)
                self._record_change(
                    row,
                    "modelling_citation_bibliographic_citation",
                    "",
                    formatted,
                    "Generated complete bibliographic citation from structured fields.",
                )
        self.pipeline._write_master_review_rows(rows)
        self._append_changelog("citation_normalization")

    def _append_changelog(self, operation: str) -> None:
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        existing: list[dict[str, Any]] = []
        if self.changelog.exists():
            try:
                payload = json.loads(self.changelog.read_text(encoding="utf-8"))
                if isinstance(payload, list):
                    existing = payload
            except json.JSONDecodeError:
                existing = []
        existing.append(
            {
                "operation": operation,
                "performed_at": now_iso(),
                "changes": self._changes,
            }
        )
        self.changelog.write_text(
            json.dumps(existing, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def materialize_master(self) -> None:
        rows = read_csv_rows(self.config.enriched_csv)
        self._changes = []
        for row in rows:
            completion = FINAL_INCLUDED_CODING_COMPLETIONS.get(row.get("class_iri", ""), {})
            if row.get("publication_eligibility_override") != "include":
                continue
            for field, value in completion.items():
                if not clean_cell(row.get(field, "")):
                    self._record_change(
                        row,
                        field,
                        row.get(field, ""),
                        value,
                        "Completed a blank included-row field from explicit evidence and established review rules.",
                    )
            if not clean_cell(row.get("reviewer", "")):
                self._record_change(row, "reviewer", "", "MM", "Recorded the reviewer who completed the final inclusion decision.")
            if not clean_cell(row.get("review_date", "")):
                self._record_change(row, "review_date", "", "2026-08-07", "Recorded the date of the final inclusion decision.")
        context = self._automated_exclusion_context(rows)

        triples_by_module: dict[str, list[tuple[str, str, str, bool]]] = {}
        for path in self.config.native_module_dir.glob("*_native_hierarchy.ttl"):
            triples_by_module[path.stem] = self.pipeline._parse_simple_ttl_triples(
                path.read_text(encoding="utf-8", errors="ignore")
            )

        for row in rows:
            iri = row.get("class_iri", "")
            flags: list[str] = []

            if clean_cell(row.get("ontology_status", "")).casefold() == "none":
                self._record_change(row, "ontology_status", row.get("ontology_status", ""), "", "Normalized literal None to an empty unknown value.")
            if not clean_cell(row.get("discovery_tier", "")):
                self._record_change(row, "discovery_tier", "", "primary_exact_label", "Legacy blank rows belong to the primary exact-label search tier.")

            arrays = {
                "definition_values_json": json_values(row, "definition_values_json", "definition", split=False),
                "comment_values_json": json_values(row, "comment_values_json", "comments", split=False),
                "synonym_values_json": json_values(row, "synonym_values_json", "synonyms", split=True),
                "parent_iri_values_json": json_values(row, "parent_iri_values_json", "parent_iris", split=True),
                "parent_label_values_json": json_values(row, "parent_label_values_json", "parent_labels", split=True),
            }
            for field, values in arrays.items():
                encoded = json.dumps(values, ensure_ascii=False)
                self._record_change(row, field, row.get(field, ""), encoded, "Added lossless multi-value serialization for TTL generation.")

            module_key = f"{safe_name(normalise_key(native_ontology_group(row)) or native_ontology_group(row))}_native_hierarchy"
            module_triples = triples_by_module.get(module_key, [])
            has_definition, has_comment, has_parent = self._quality_presence(module_triples, iri)
            has_definition = has_definition or bool(arrays["definition_values_json"])
            has_comment = has_comment or bool(arrays["comment_values_json"])
            has_parent = has_parent or bool(arrays["parent_iri_values_json"])

            quality_fields = [
                ("definition_quality", has_definition),
                ("comment_quality", has_comment),
                ("parentage_quality", has_parent),
            ]
            for field, present in quality_fields:
                old = clean_cell(row.get(field, ""))
                if present and old == "absent":
                    self._record_change(row, field, old, "partial", "Evidence is present, so the field cannot be coded absent; partial is the conservative correction.")
                elif not present and old not in {"", "absent", "not_applicable"}:
                    self._record_change(row, field, old, "absent", "No corresponding evidence is present in the native module or master CSV.")

            auto_reason, auto_detail = self._automated_exclusion_reason(row, context)
            manual = clean_cell(row.get("manual_include_status", ""))
            override = clean_cell(row.get("publication_eligibility_override", ""))
            if override in {"include", "exclude"}:
                effective = override
                basis = "user_publication_override"
                rule = "publication_eligibility_override"
                reason = "" if override == "include" else (auto_reason or row.get("manual_exclusion_reason", "") or "user_exclusion")
            elif manual == "include" and auto_reason:
                effective = "needs_user_decision"
                basis = "manual_rule_conflict"
                rule = auto_reason
                reason = auto_reason
                flags.append("eligibility_manual_rule_conflict")
            elif manual == "exclude":
                effective = "exclude"
                basis = "manual_review"
                rule = "manual_include_status"
                reason = clean_cell(row.get("manual_exclusion_reason", "")) or "manual_exclusion"
            elif auto_reason:
                effective = "exclude"
                basis = "deterministic_scope_rule"
                rule = auto_reason
                reason = auto_reason
            elif manual == "include":
                effective = "include"
                basis = "manual_review"
                rule = "manual_include_status"
                reason = ""
            else:
                effective = "needs_user_decision"
                basis = "unresolved_eligibility"
                rule = "manual_status_missing"
                reason = ""
                flags.append("eligibility_unresolved")

            for field, value in {
                "effective_synthesis_status": effective,
                "effective_synthesis_exclusion_reason": reason,
                "effective_decision_basis": basis,
                "effective_decision_rule": rule,
            }.items():
                self._record_change(row, field, row.get(field, ""), value, "Materialized the final synthesis decision from manual review, explicit policies, and deterministic rules.")
            if clean_cell(row.get("publication_ambiguity_note", "")) == WITHDRAWN_IRI_RULE_NOTE:
                self._record_change(
                    row,
                    "publication_ambiguity_note",
                    row.get("publication_ambiguity_note", ""),
                    NEUTRAL_IRI_REVIEW_NOTE,
                    "Replaced wording from the withdrawn IRI-format exclusion rule with a neutral review instruction.",
                )
            if auto_detail and auto_reason:
                note = clean_cell(row.get("publication_ambiguity_note", ""))
                if not note:
                    row["publication_ambiguity_note"] = auto_detail

            citation_status = clean_cell(row.get("modelling_citation_status", "")).lower()
            citation_approved = clean_cell(row.get("modelling_citation_approved", "")).lower()
            citation_payload = any(clean_cell(row.get(field, "")) for field in CITATION_REFERENCE_COLUMNS)
            if effective in {"include", "needs_user_decision"} and not citation_status:
                flags.append("citation_status_unreviewed")
            if effective in {"include", "needs_user_decision"} and not citation_approved:
                flags.append("citation_approval_unreviewed")
            if citation_status == "no_citation" and citation_approved == "yes":
                flags.append("citation_state_conflict")
            if citation_approved == "yes" and citation_payload:
                required = [
                    "modelling_citation_publication_title",
                    "modelling_citation_authors",
                    "modelling_citation_year",
                    "modelling_citation_venue",
                ]
                if any(not clean_cell(row.get(field, "")) for field in required):
                    flags.append("citation_metadata_incomplete")

            comment = clean_cell(row.get("review_comment", ""))
            if comment and SUBJECTIVE_COMMENT_PATTERN.search(comment):
                proposal = self._neutral_comment_proposal(comment)
                self._record_change(
                    row,
                    "publication_review_comment_proposed",
                    row.get("publication_review_comment_proposed", ""),
                    proposal,
                    "Prepared a neutral publication wording proposal without replacing the primary review comment.",
                )
                if row.get("publication_comment_status") not in {"approved", "rejected"}:
                    row["publication_comment_status"] = "needs_review"
                if row.get("publication_comment_status") == "needs_review":
                    flags.append("publication_comment_needs_review")
            elif comment and not row.get("publication_comment_status"):
                row["publication_comment_status"] = "not_needed"

            row["publication_ambiguity_flags"] = "; ".join(dict.fromkeys(flags))

        self.pipeline._write_master_review_rows(rows)
        self._append_changelog("materialize_master")
        self.write_schema_and_dictionary(rows)

    def write_schema_and_dictionary(self, rows: list[dict[str, str]] | None = None) -> None:
        rows = rows or read_csv_rows(self.config.enriched_csv)
        fieldnames = list(rows[0].keys()) if rows else []
        schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": "Disease ontology artifact-evaluation master row",
            "type": "object",
            "required": ["class_iri", "effective_synthesis_status"],
            "additionalProperties": False,
            "properties": {
                field: {
                    "type": "string",
                    **({"enum": CONTROLLED_VALUES[field]} if field in CONTROLLED_VALUES else {}),
                }
                for field in fieldnames
            },
        }
        schema_path = self.audit_dir / "disease_terms_review_enriched.schema.json"
        dictionary_path = self.audit_dir / "disease_terms_review_enriched_data_dictionary.md"
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        schema_path.write_text(json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        lines = [
            "# Disease Ontology Artifact-Evaluation Master Data Dictionary",
            "",
            "`disease_terms_review_enriched.csv` is the sole editable master table. All TTL files and reports are generated from it.",
            "",
            "| Column | Controlled values |",
            "|---|---|",
        ]
        for field in fieldnames:
            values = ", ".join(f"`{value}`" if value else "blank" for value in CONTROLLED_VALUES.get(field, []))
            lines.append(f"| `{field}` | {values or 'Free text, identifier, provenance value, or generated field'} |")
        dictionary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def audit(self) -> dict[str, Any]:
        rows = read_csv_rows(self.config.enriched_csv)
        ambiguity_entries: list[dict[str, str]] = []
        for row in rows:
            flags = split_semicolon(row.get("publication_ambiguity_flags", ""))
            if not flags:
                continue
            ambiguity_entries.append(
                {
                    "class_iri": row.get("class_iri", ""),
                    "ontology": native_ontology_group(row),
                    "label": row.get("preferred_label", ""),
                    "flags": "; ".join(flags),
                    "manual_status": row.get("manual_include_status", ""),
                    "effective_status": row.get("effective_synthesis_status", ""),
                    "rule": row.get("effective_decision_rule", ""),
                    "evidence_status": row.get("hierarchy_evidence_status", ""),
                    "citation_status": row.get("modelling_citation_status", ""),
                    "citation_approved": row.get("modelling_citation_approved", ""),
                    "review_comment": row.get("review_comment", ""),
                    "proposed_comment": row.get("publication_review_comment_proposed", ""),
                }
            )

        edge_modules: dict[tuple[str, str], set[str]] = defaultdict(set)
        target_module_mismatches: list[dict[str, str]] = []
        for path in self.config.native_module_dir.glob("*_native_hierarchy.ttl"):
            module_key = path.stem.removesuffix("_native_hierarchy")
            triples = self.pipeline._parse_simple_ttl_triples(path.read_text(encoding="utf-8", errors="ignore"))
            for subject, predicate, obj, object_is_iri in triples:
                if predicate == RDFS_SUBCLASS_OF and object_is_iri:
                    edge_modules[(subject, obj)].add(module_key)

        for row in rows:
            expected = safe_name(normalise_key(native_ontology_group(row)) or native_ontology_group(row))
            module_iri = row.get("hierarchy_module_iri", "")
            actual = safe_name(module_iri.removeprefix(REVIEW_MODULE_BASE_IRI)) if module_iri else ""
            if actual and expected != actual:
                target_module_mismatches.append(
                    {
                        "class_iri": row.get("class_iri", ""),
                        "expected_module": expected,
                        "actual_module": actual,
                    }
                )

        cross_module_edges = [
            {"subject": subject, "parent": parent, "modules": sorted(modules)}
            for (subject, parent), modules in edge_modules.items()
            if len(modules) > 1
        ]

        approved_incomplete = []
        citation_unreviewed = []
        for row in rows:
            if row.get("effective_synthesis_status") not in {"include", "needs_user_decision"}:
                continue
            approved = clean_cell(row.get("modelling_citation_approved", "")).lower()
            status = clean_cell(row.get("modelling_citation_status", "")).lower()
            if not status or approved == "":
                citation_unreviewed.append({"ontology": native_ontology_group(row), "class_iri": row.get("class_iri", "")})
            if approved == "yes":
                missing = [
                    field for field in [
                        "modelling_citation_publication_title",
                        "modelling_citation_authors",
                        "modelling_citation_year",
                        "modelling_citation_venue",
                    ]
                    if not clean_cell(row.get(field, ""))
                ]
                if missing:
                    approved_incomplete.append(
                        {"ontology": native_ontology_group(row), "class_iri": row.get("class_iri", ""), "missing": missing}
                    )

        ttl_checks = {}
        for path in [self.config.review_ontology_ttl, self.config.synthesis_ontology_ttl, self.config.review_core_ttl]:
            text = path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""
            ttl_checks[path.name] = {
                "exists": path.exists(),
                "contains_file_iri": "file:///" in text,
                "contains_reserved_review_namespace": "https://example.org/disease-review" in text,
                "contains_deprecated_web_namespace": "https://w3id.org/disease-ontology-review" in text,
                "sha256": sha256(path) if path.exists() else "",
            }

        human_tasks = [
            "Complete and reconcile the prespecified 50-class independent stratified validation sample.",
            "Reconcile the draft reference inventory in Zotero and export it in the selected journal's style.",
        ]
        if ambiguity_entries:
            human_tasks.append("Approve or edit unresolved publication decisions in the review UI.")

        report = {
            "generated_at": now_iso(),
            "master_csv": str(self.config.enriched_csv),
            "master_sha256": sha256(self.config.enriched_csv),
            "row_count": len(rows),
            "unique_class_iris": len({row.get("class_iri", "") for row in rows if row.get("class_iri")}),
            "effective_synthesis_status_counts": dict(Counter(row.get("effective_synthesis_status", "") for row in rows)),
            "evidence_status_counts": dict(Counter(row.get("hierarchy_evidence_status", "") for row in rows)),
            "ambiguity_count": len(ambiguity_entries),
            "ambiguities": ambiguity_entries,
            "citation_unreviewed": citation_unreviewed,
            "approved_citations_incomplete": approved_incomplete,
            "target_module_mismatches": target_module_mismatches,
            "cross_module_duplicate_edges": cross_module_edges,
            "ttl_checks": ttl_checks,
            "external_human_tasks": human_tasks,
        }
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        self.report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        self._write_audit_markdown(report)
        return report

    def _write_audit_markdown(self, report: dict[str, Any]) -> None:
        lines = [
            "# Publication Readiness Report",
            "",
            f"Generated: `{report['generated_at']}`",
            "",
            f"- Master rows: {report['row_count']}",
            f"- Unique class IRIs: {report['unique_class_iris']}",
            f"- Effective status: `{json.dumps(report['effective_synthesis_status_counts'], sort_keys=True)}`",
            f"- Evidence status: `{json.dumps(report['evidence_status_counts'], sort_keys=True)}`",
            f"- Ambiguous decisions: {report['ambiguity_count']}",
            f"- Citation assignments still unreviewed: {len(report['citation_unreviewed'])}",
            f"- Approved citations with incomplete core metadata: {len(report['approved_citations_incomplete'])}",
            f"- Target/module mismatches: {len(report['target_module_mismatches'])}",
            f"- Cross-module duplicate superclass edges: {len(report['cross_module_duplicate_edges'])}",
            "",
            "## Ambiguous Decisions",
            "",
            "| Ontology | Class | Flags | Manual | Effective | Rule |",
            "|---|---|---|---|---|---|",
        ]
        for item in report["ambiguities"]:
            lines.append(
                "| {ontology} | `{class_iri}` ({label}) | {flags} | {manual_status} | {effective_status} | {rule} |".format(
                    **{key: str(value).replace("|", "\\|") for key, value in item.items()}
                )
            )
        lines.extend(["", "## Remaining Human Tasks", ""])
        lines.extend(f"- {task}" for task in report["external_human_tasks"])
        self.report_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def export(self) -> None:
        self.pipeline.export_review_ontology(argparse.Namespace())

    def package_release(self) -> Path:
        report = self.audit()
        release_date = datetime.now().astimezone().date().isoformat()
        target = self.release_dir / "release_candidate"
        if target.exists():
            shutil.rmtree(target)
        for directory in ["ontology", "ontology/native_hierarchy_modules", "docs", "figures"]:
            (target / directory).mkdir(parents=True, exist_ok=True)

        copies = {
            self.config.review_core_ttl: target / "ontology" / self.config.review_core_ttl.name,
            self.config.review_ontology_ttl: target / "ontology" / self.config.review_ontology_ttl.name,
            self.config.synthesis_ontology_ttl: target / "ontology" / self.config.synthesis_ontology_ttl.name,
            self.config.ontology_catalog: target / "ontology" / self.config.ontology_catalog.name,
            self.review_dir.parent / "LICENSE": target / "LICENSE",
            self.review_dir / "Disease_Ontology_Artifact_Evaluation_Manuscript.docx": target / "docs" / "Disease_Ontology_Artifact_Evaluation_Manuscript.docx",
            self.review_dir / "Figures" / "artifact_selection_flow_diagram.png": target / "figures" / "artifact_selection_flow_diagram.png",
            self.review_dir / "Figures" / "artifact_selection_flow_diagram.svg": target / "figures" / "artifact_selection_flow_diagram.svg",
            self.review_dir / "Figures" / "disease_model_evidence_summary.png": target / "figures" / "disease_model_evidence_summary.png",
            self.review_dir / "Figures" / "disease_model_evidence_summary.svg": target / "figures" / "disease_model_evidence_summary.svg",
        }
        for source, destination in copies.items():
            if source.exists():
                shutil.copy2(source, destination)
        for source in sorted(self.config.native_module_dir.glob("*_native_hierarchy.ttl")):
            shutil.copy2(source, target / "ontology" / "native_hierarchy_modules" / source.name)

        readme = f"""# Disease Ontology Artifact-Evaluation Release Candidate

Generated: {report['generated_at']}

This submission package contains the manuscript, main figures, and serialized ontology supplements. The internal working CSV, source code, workflow documents, and audit files are intentionally not included.

## Contents

- `ontology/disease_terms_review.ttl`: all {report['row_count']} screening/evidence records.
- `ontology/disease_terms_synthesis.ttl`: included-only synthesis view.
- `ontology/review_core.ttl`: review annotation-property declarations.
- `ontology/native_hierarchy_modules/`: subject-sanitized native evidence modules.
- `ontology/catalog-v001.xml`: local UUID-URN import resolution.
- `figures/`: manuscript Figures 1 and 2 in PNG and SVG formats.
- `docs/Disease_Ontology_Artifact_Evaluation_Manuscript.docx`: submission manuscript with the authors' current citation edits.

## Current Decision State

- Included: {report['effective_synthesis_status_counts'].get('include', 0)}
- Excluded: {report['effective_synthesis_status_counts'].get('exclude', 0)}
- Needs adjudication: {report['effective_synthesis_status_counts'].get('needs_user_decision', 0)}

This is a release candidate, not the final scholarly release. Independent stratified validation and reference reconciliation remain author tasks. The evidence ontology uses non-resolving UUID URNs and is intended to travel with the publication as a self-contained supplement. A broader philosophical-literature synthesis is a separate project and is not part of this artifact-evaluation denominator.

The package is MIT-licensed as specified in `LICENSE`. Extracted source-ontology statements retain their original provenance and any rights held by their source publishers.
"""
        (target / "README.md").write_text(readme, encoding="utf-8")

        archive = self.release_dir / f"disease_ontology_artifact_evaluation_release_candidate_{release_date}.tar.gz"
        if archive.exists():
            archive.unlink()
        with tarfile.open(archive, "w:gz") as handle:
            handle.add(target, arcname=target.name)
        print(f"Packaged release candidate -> {archive}")
        return archive

    def run_all(self, *, allow_network: bool = True, make_baseline: bool = False) -> dict[str, Any]:
        if make_baseline:
            self.baseline()
        self.build_native_modules(allow_network=allow_network)
        self.enrich_citations()
        self.materialize_master()
        self.export()
        return self.audit()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=["baseline", "build-native-modules", "citations", "materialize", "export", "audit", "package", "all"],
    )
    parser.add_argument("--no-network", action="store_true", help="Do not call registry or bibliographic APIs.")
    parser.add_argument("--baseline", action="store_true", help="Create a baseline archive before the all action.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    manager = PublicationReadiness()
    if args.action == "baseline":
        print(manager.baseline())
    elif args.action == "build-native-modules":
        manager.build_native_modules(allow_network=not args.no_network)
    elif args.action == "citations":
        manager.enrich_citations()
    elif args.action == "materialize":
        manager.materialize_master()
    elif args.action == "export":
        manager.export()
    elif args.action == "package":
        manager.package_release()
    elif args.action == "audit":
        print(json.dumps(manager.audit(), ensure_ascii=False, indent=2))
    elif args.action == "all":
        manager.run_all(allow_network=not args.no_network, make_baseline=args.baseline)


if __name__ == "__main__":
    main()
