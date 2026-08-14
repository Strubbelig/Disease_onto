#!/usr/bin/env python3
"""Regression checks for the disease ontology publication release."""

from __future__ import annotations

import json
import sys
import unittest
from collections import defaultdict
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from publication_readiness import PublicationReadiness, normalise_key  # noqa: E402
from review_extraction_pipeline import (  # noqa: E402
    CITATION_REFERENCE_COLUMNS,
    IAO_DEFINITION,
    REVIEW_MODULE_BASE_IRI,
    RDFS_SUBCLASS_OF,
    native_ontology_group,
    read_csv_rows,
    safe_name,
)


class PublicationReadinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manager = PublicationReadiness()
        cls.pipeline = cls.manager.pipeline
        cls.rows = read_csv_rows(cls.manager.config.enriched_csv)

    def test_master_keys_and_json_values(self) -> None:
        iris = [row["class_iri"] for row in self.rows]
        self.assertEqual(len(iris), len(set(iris)))
        self.assertTrue(all(row.get("effective_synthesis_status") for row in self.rows))
        for row in self.rows:
            for field in [
                "definition_values_json",
                "comment_values_json",
                "synonym_values_json",
                "parent_iri_values_json",
                "parent_label_values_json",
            ]:
                self.assertIsInstance(json.loads(row[field]), list, (row["class_iri"], field))

    def test_included_rows_have_complete_primary_coding(self) -> None:
        required = [
            "ontology_type_manual",
            "disease_model_category",
            "ontological_category",
            "pathological_grounding",
            "crisp_vs_graded",
            "reality_vs_classification",
            "definition_quality",
            "comment_quality",
            "parentage_quality",
            "entity_quality_score",
            "reviewer",
            "review_date",
        ]
        for row in self.rows:
            if row.get("effective_synthesis_status") == "include":
                missing = [field for field in required if not row.get(field, "")]
                self.assertEqual(missing, [], row["class_iri"])

    def test_insufficient_evidence_does_not_override_human_inclusion(self) -> None:
        included_sparse_rows = [
            row
            for row in self.rows
            if row.get("hierarchy_evidence_status") == "insufficient_metadata"
            and row.get("effective_synthesis_status") == "include"
        ]
        self.assertTrue(included_sparse_rows)
        for row in included_sparse_rows:
            self.assertIn(
                "include",
                {
                    row.get("manual_include_status"),
                    row.get("publication_eligibility_override"),
                },
                row["class_iri"],
            )

    def test_rejected_or_absent_citations_have_no_payload(self) -> None:
        for row in self.rows:
            if row.get("modelling_citation_approved") in {"no", "none"}:
                self.assertEqual(row.get("modelling_citation_status"), "no_citation")
                self.assertFalse(
                    any(row.get(field) for field in CITATION_REFERENCE_COLUMNS),
                    row["class_iri"],
                )

    def test_ontology_level_citation_decisions_are_consistent(self) -> None:
        groups: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in self.rows:
            key = normalise_key(
                row.get("modelling_citation_source_ontology_id", "")
                or row.get("native_ontology_guess", "")
                or row.get("ontology", "")
            )
            if key:
                groups[key].append(row)
        for key, group_rows in groups.items():
            approved = {row.get("modelling_citation_approved", "") for row in group_rows}
            if "yes" in approved and not ({"none", "no"} & approved):
                self.assertNotIn("", approved, key)
            if ({"none", "no"} & approved) and "yes" not in approved:
                self.assertNotIn("", approved, key)

    def test_canonical_hierarchies_are_native(self) -> None:
        expected = {
            "doid": ("http://purl.obolibrary.org/obo/DOID_4", set()),
            "ogms": (
                "http://purl.obolibrary.org/obo/OGMS_0000031",
                {"http://purl.obolibrary.org/obo/BFO_0000016"},
            ),
            "mondo": ("http://purl.obolibrary.org/obo/MONDO_0000001", set()),
        }
        for key, (iri, wanted_parents) in expected.items():
            path = self.manager.config.native_module_dir / f"{key}_native_hierarchy.ttl"
            triples = self.pipeline._parse_simple_ttl_triples(path.read_text(encoding="utf-8"))
            parents = {
                obj
                for subject, predicate, obj, object_is_iri in triples
                if subject == iri and predicate == RDFS_SUBCLASS_OF and object_is_iri
            }
            self.assertEqual(parents, wanted_parents, key)

    def test_superclass_subjects_are_isolated_to_one_native_module(self) -> None:
        modules_by_subject: dict[str, set[str]] = defaultdict(set)
        for path in self.manager.config.native_module_dir.glob("*_native_hierarchy.ttl"):
            module = path.stem.removesuffix("_native_hierarchy")
            triples = self.pipeline._parse_simple_ttl_triples(path.read_text(encoding="utf-8"))
            for subject, predicate, _, object_is_iri in triples:
                if predicate == RDFS_SUBCLASS_OF and object_is_iri:
                    modules_by_subject[subject].add(module)
        duplicated = {subject: modules for subject, modules in modules_by_subject.items() if len(modules) > 1}
        self.assertEqual(duplicated, {})

    def test_target_module_assignments_match_native_group(self) -> None:
        for row in self.rows:
            expected = safe_name(normalise_key(native_ontology_group(row)) or native_ontology_group(row))
            actual = row.get("hierarchy_module_iri", "").removeprefix(REVIEW_MODULE_BASE_IRI)
            self.assertEqual(actual, expected, row["class_iri"])

    def test_hierarchy_source_labels_are_unique(self) -> None:
        for row in self.rows:
            labels = [part.strip() for part in row.get("hierarchy_module_source", "").split(";") if part.strip()]
            self.assertEqual(len(labels), len(set(labels)), row["class_iri"])

    def test_semicolon_definition_is_preserved_as_one_literal(self) -> None:
        row = next(item for item in self.rows if item.get("ontology") == "LTER-CV")
        expected = json.loads(row["definition_values_json"])
        path = self.manager.config.native_module_dir / "lter_cv_native_hierarchy.ttl"
        triples = self.pipeline._parse_simple_ttl_triples(path.read_text(encoding="utf-8"))
        values = [
            obj
            for subject, predicate, obj, object_is_iri in triples
            if subject == row["class_iri"] and predicate == IAO_DEFINITION and not object_is_iri
        ]
        self.assertEqual(len(expected), 1)
        self.assertEqual(len(values), 1)
        self.assertIn("; distinct from injury", values[0])
        self.assertTrue(expected[0].startswith(values[0]))

    def test_release_iris_are_portable(self) -> None:
        for path in [
            self.manager.config.review_core_ttl,
            self.manager.config.review_ontology_ttl,
            self.manager.config.synthesis_ontology_ttl,
        ]:
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("file:///", text, path.name)
            self.assertNotIn("https://example.org/disease-review", text, path.name)

    def test_neutral_comment_proposals_are_grammatical(self) -> None:
        examples = {
            "Many strange most probably Protege generated error classes in the ontology":
                "The ontology contains many probable Protege-generated error classes.",
            "This has obviously a very narrow scope.":
                "This has an application-specific scope.",
            "Strangely, COPD is_a ClinicalCondition.":
                "COPD is_a ClinicalCondition.",
            "Very strange hierachy of Disease is_a Quality.":
                "The hierarchy of Disease is_a Quality is internally inconsistent.",
            "This is a wrong subsumption.":
                "This is an incorrect subsumption.",
        }
        for source, expected in examples.items():
            self.assertEqual(self.manager._neutral_comment_proposal(source), expected)


if __name__ == "__main__":
    unittest.main()
