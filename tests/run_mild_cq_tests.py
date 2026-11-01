#!/opt/anaconda3/envs/onto_env/bin/python
"""
Reasoner-checked test of the six MILD competency questions.

    /opt/anaconda3/envs/onto_env/bin/python tests/run_mild_cq_tests.py            # ELK
    ... run_mild_cq_tests.py --reasoner HermiT                                   # slow (hours)
    ... run_mild_cq_tests.py --mild "mild_2026-10-30g.ttl"                       # pin a MILD file
    ... run_mild_cq_tests.py --dump-queries tests/mild_cq_queries.md             # write the query list
    ... run_mild_cq_tests.py --work-dir some/dir                                 # keep merged + reasoned files

What it does
  1. Finds the current MILD file: the INPUT= line of build_disease_proposal.sh
     (the pipeline's single source of truth), unless --mild is given.
  2. Writes a catalog that maps the MILD IRI to that file, the module IRIs to
     the local module files, and the BFO 2020 / RO import IRIs to the local
     copies in "Import ontologies" (the same mapping the pipeline uses).
  3. ROBOT merge: test individuals + the whole MILD import closure -> one file.
  4. ROBOT reason (ELK by default): must succeed, i.e. consistent and no
     unsatisfiable class. Inferred class assertions (direct and indirect) are
     written into the output so SPARQL can see them.
  5. ROBOT reason a second time on test + probe classes: every probe that the
     questions say must be unsatisfiable has to come back unsatisfiable.
  6. Every competency question is decided by explicit SPARQL ASK queries over
     the reasoned output (rdflib). Expected entailments must be true, expected
     non-entailments must be false. Each check prints the query that decided
     it. A query that raises an error fails its question; the run exits 1 if
     any question fails. Nothing is skipped silently.

Exit code 0 = six PASS lines.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
import traceback
from pathlib import Path
from urllib.parse import quote

try:
    import rdflib
except ImportError:  # pragma: no cover
    sys.exit("rdflib missing: run with /opt/anaconda3/envs/onto_env/bin/python")

HERE = Path(__file__).resolve().parent                 # .../Disease ontologies/tests
DISEASE_DIR = HERE.parent                              # .../Disease ontologies
ONTOLOGY_DIR = DISEASE_DIR.parent                      # .../Ontology
MODULE_DIR = DISEASE_DIR / "Disease ontology modules"
IMPORT_DIR = ONTOLOGY_DIR / "Import ontologies"
BUILD_SCRIPT = DISEASE_DIR / "build_disease_proposal.sh"
TEST_TTL = HERE / "mild_cq_test_2026-10-30.ttl"
PROBE_TTL = HERE / "mild_cq_probes_2026-10-30.ttl"

ROBOT_JAR = "/usr/local/bin/robot.jar"
JAVA_OPTS = ["-Xmx10g"]

MILD_IRI = "https://bioportal.bioontology.org/ontologies/MILD"
MILD_NS = MILD_IRI + "/"
MODULE_NS = MILD_IRI + "/modules/"
CQ_NS = "https://bioportal.bioontology.org/ontologies/MILD/tests/cq_2026-10-30#"
PROBE_NS = "https://bioportal.bioontology.org/ontologies/MILD/tests/cq_probes_2026-10-30#"
OBO = "http://purl.obolibrary.org/obo/"

# The two whole ontologies MILD imports directly (curator, 2026-10-30) and the
# local files that stand for them. If MILD ever imports another whole ontology,
# the merge step reports the unresolved IRI and stops.
WHOLE_IMPORTS = {
    "http://purl.obolibrary.org/obo/bfo/2020/bfo-core.owl": IMPORT_DIR / "bfo-core2020.owl",
    "http://purl.obolibrary.org/obo/ro/releases/2025-12-17/ro.owl": IMPORT_DIR / "ro.owl",
}

PREFIXES = textwrap.dedent(f"""\
    PREFIX owl:  <http://www.w3.org/2002/07/owl#>
    PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX obo:  <{OBO}>
    PREFIX mild: <{MILD_NS}>
    PREFIX cq:   <{CQ_NS}>
    """)

# ---------------------------------------------------------------------------
# The checks. One list per competency question.
#   kind "entail"     : ASK must be true
#   kind "nonentail"  : ASK must be false
#   kind "probe"      : the probe class must be unsatisfiable in the probe run
#   kind "probe-info" : reported, never decides the question
# Every ASK is written against the reasoned output, which contains the asserted
# axioms plus the inferred subclass axioms and class assertions.
# ---------------------------------------------------------------------------

# Reusable TBox fragments ----------------------------------------------------

# Any class reachable upwards from ?start (including itself) that carries a
# restriction forcing at least one filler of a class under ?fillerRoot:
# `some`, `min n`/`exactly n` (via owl:onClass) or `value`. Restrictions can sit
# directly as superclass or inside an intersection used as superclass or as
# equivalent class.
def forced_filler_tbox(start: str, filler_root: str) -> str:
    return textwrap.dedent(f"""\
        ASK {{
          {start} rdfs:subClassOf* ?c .
          {{ ?c rdfs:subClassOf ?r }}
          UNION {{ ?c owl:equivalentClass ?r }}
          UNION {{ ?c rdfs:subClassOf/owl:intersectionOf/rdf:rest*/rdf:first ?r }}
          UNION {{ ?c owl:equivalentClass/owl:intersectionOf/rdf:rest*/rdf:first ?r }}
          ?r a owl:Restriction .
          {{ ?r owl:someValuesFrom ?f }}
          UNION {{ ?r owl:onClass ?f . FILTER EXISTS {{ {{ ?r owl:minQualifiedCardinality ?n }} UNION {{ ?r owl:qualifiedCardinality ?n }} }} }}
          UNION {{ ?r owl:hasValue ?v . ?v a ?f }}
          ?f rdfs:subClassOf* {filler_root} .
        }}""")

# Same, but keyed on the property: any forcing restriction on ?prop or one of
# its sub-properties reachable upwards from ?start.
def forced_property_tbox(start: str, prop: str) -> str:
    return textwrap.dedent(f"""\
        ASK {{
          {start} rdfs:subClassOf* ?c .
          {{ ?c rdfs:subClassOf ?r }}
          UNION {{ ?c owl:equivalentClass ?r }}
          UNION {{ ?c rdfs:subClassOf/owl:intersectionOf/rdf:rest*/rdf:first ?r }}
          UNION {{ ?c owl:equivalentClass/owl:intersectionOf/rdf:rest*/rdf:first ?r }}
          ?r a owl:Restriction ; owl:onProperty ?p .
          ?p rdfs:subPropertyOf* {prop} .
          {{ ?r owl:someValuesFrom ?f }}
          UNION {{ ?r owl:minQualifiedCardinality ?n }}
          UNION {{ ?r owl:qualifiedCardinality ?n }}
          UNION {{ ?r owl:minCardinality ?n }}
          UNION {{ ?r owl:cardinality ?n }}
          UNION {{ ?r owl:hasValue ?v }}
        }}""")

# Could ?prop (or a super-property of it) force two individuals to be one?
def identity_forcing_property(prop: str) -> str:
    return textwrap.dedent(f"""\
        ASK {{
          {prop} rdfs:subPropertyOf* ?p .
          {{ ?p a owl:FunctionalProperty }} UNION {{ ?p a owl:InverseFunctionalProperty }}
        }}""")

# Any max/exact cardinality on ?prop (or a sub-property) among the superclasses of ?start?
def upper_cardinality_tbox(start: str, prop: str) -> str:
    return textwrap.dedent(f"""\
        ASK {{
          {start} rdfs:subClassOf* ?c .
          {{ ?c rdfs:subClassOf ?r }}
          UNION {{ ?c owl:equivalentClass ?r }}
          UNION {{ ?c rdfs:subClassOf/owl:intersectionOf/rdf:rest*/rdf:first ?r }}
          UNION {{ ?c owl:equivalentClass/owl:intersectionOf/rdf:rest*/rdf:first ?r }}
          ?r a owl:Restriction ; owl:onProperty ?p .
          ?p rdfs:subPropertyOf* {prop} .
          {{ ?r owl:maxQualifiedCardinality ?n }} UNION {{ ?r owl:qualifiedCardinality ?n }}
          UNION {{ ?r owl:maxCardinality ?n }} UNION {{ ?r owl:cardinality ?n }}
          UNION {{ ?r owl:allValuesFrom ?f }}
        }}""")

def same_as(a: str, b: str) -> str:
    return f"ASK {{ {{ {a} owl:sameAs {b} }} UNION {{ {b} owl:sameAs {a} }} }}"

def has_type(ind: str, cls: str) -> str:
    return f"ASK {{ {ind} a {cls} }}"

def triple(s: str, p: str, o: str) -> str:
    return f"ASK {{ {s} {p} {o} }}"

ANY_SAMEAS_IN_TEST = textwrap.dedent(f"""\
    ASK {{
      ?a owl:sameAs ?b .
      FILTER(?a != ?b)
      FILTER(STRSTARTS(STR(?a), "{CQ_NS}") || STRSTARTS(STR(?b), "{CQ_NS}"))
    }}""")

CQS = [
    {
        "id": "CQ1",
        "question": "Can a patient have a pathological disorder without a diagnosis?",
        "expected_answer": "yes",
        "how": "disorder_1 is asserted only as a material entity that has a pathological quality and is part of "
               "patient_1; no diagnostic result exists for it. The reasoner must still classify it as a material "
               "disease entity, and nothing in the axioms may force a diagnostic result.",
        "checks": [
            ("entail", "disorder_1 is inferred to be a material disease entity (MILD_120020) from 'material entity and has quality some pathological'",
             has_type("cq:disorder_1", "mild:MILD_120020")),
            ("entail", "disorder_1 is inferred to be an independent continuant (BFO_0000004), i.e. the BFO backbone is in the closure",
             has_type("cq:disorder_1", "obo:BFO_0000004")),
            ("entail", "disorder_1 is part of patient_1 (the pattern of the question)",
             triple("cq:disorder_1", "obo:BFO_0000050", "cq:patient_1")),
            ("nonentail", "no information entity is about disorder_1 (no diagnostic result inferred)",
             "ASK { ?x obo:IAO_0000136 cq:disorder_1 }"),
            ("nonentail", "no individual of the CQ1 pattern is a disease diagnostic result (MILD_120024)",
             textwrap.dedent(f"""\
                ASK {{ ?x a mild:MILD_120024 . FILTER(?x IN (cq:patient_1, cq:disorder_1, cq:pathological_1)) }}""")),
            ("nonentail", "class level: no superclass of material disease entity forces (some/min/value) a filler under disease diagnostic result",
             forced_filler_tbox("mild:MILD_120020", "mild:MILD_120024")),
        ],
    },
    {
        "id": "CQ2",
        "question": "Can two diagnostic results group overlapping but non-identical disorder sets?",
        "expected_answer": "yes",
        "how": "diagnosis_A is about disorders 1 and 2, diagnosis_B about disorders 2 and 3; disease_A2 and disease_B2 "
               "have the matching parts. Both pairs are asserted owl:differentFrom. The ontology must stay consistent "
               "and infer no owl:sameAs; at class level nothing may make 'is about' or 'has part' functional or "
               "cap the number of disorders a result is about. Under ELK the differentFrom assertions are ignored "
               "(OWL 2 EL), so the identity checks are structural; under HermiT they are complete.",
        "checks": [
            ("entail", "diagnosis_A is inferred to be an information content entity (IAO_0000030)",
             has_type("cq:diagnosis_A", "obo:IAO_0000030")),
            ("entail", "diagnosis_A and diagnosis_B both are about disorder_2_2 (the overlap is representable)",
             "ASK { cq:diagnosis_A obo:IAO_0000136 cq:disorder_2_2 . cq:diagnosis_B obo:IAO_0000136 cq:disorder_2_2 }"),
            ("nonentail", "diagnosis_A and diagnosis_B are not inferred identical",
             same_as("cq:diagnosis_A", "cq:diagnosis_B")),
            ("nonentail", "disease_A2 and disease_B2 are not inferred identical",
             same_as("cq:disease_A2", "cq:disease_B2")),
            ("nonentail", "class level: 'is about' (IAO_0000136) is neither functional nor inverse functional, nor is any super-property",
             identity_forcing_property("obo:IAO_0000136")),
            ("nonentail", "class level: 'has part' (BFO_0000051) is neither functional nor inverse functional, nor is any super-property",
             identity_forcing_property("obo:BFO_0000051")),
            ("nonentail", "class level: no superclass of disease diagnostic result caps or closes 'is about' (max/exact cardinality, only)",
             upper_cardinality_tbox("mild:MILD_120024", "obo:IAO_0000136")),
        ],
    },
    {
        "id": "CQ3",
        "question": "Can a predisposition exist without the target disorder already existing?",
        "expected_answer": "yes",
        "how": "predisposition_1 (a pathological genetic predisposition) inheres in patient_3 and has variant_1 as "
               "material basis; no realization is asserted. The reasoner must classify it as a disease "
               "predisposition and a tendency, and no axiom on it or on any superclass may force a realization or "
               "a disorder development process. A probe class shows a predisposition can never be a material "
               "disease entity. patient_3r carries the realized branch: a predisposition realizing disorder "
               "development process that realizes predisposition_1r and has output target_disorder_r.",
        "checks": [
            ("entail", "predisposition_1 is inferred to be a disease predisposition (MILD_120023)",
             has_type("cq:predisposition_1", "mild:MILD_120023")),
            ("entail", "predisposition_1 is inferred to be a tendency (MILD_120005) and a BFO realizable entity (BFO_0000017)",
             "ASK { cq:predisposition_1 a mild:MILD_120005 , obo:BFO_0000017 }"),
            ("entail", "variant_1 is inferred to be a material entity (BFO_0000040)",
             has_type("cq:variant_1", "obo:BFO_0000040")),
            ("nonentail", "predisposition_1 has no realization (BFO_0000054) and nothing realizes it (BFO_0000055)",
             "ASK { { cq:predisposition_1 obo:BFO_0000054 ?p } UNION { ?p obo:BFO_0000055 cq:predisposition_1 } }"),
            ("nonentail", "no individual of the unrealized pattern is a disorder development process (MILD_120021) or a process (BFO_0000015)",
             textwrap.dedent("""\
                ASK { ?x a ?t . FILTER(?t IN (mild:MILD_120021, obo:BFO_0000015))
                      FILTER(?x IN (cq:patient_3, cq:variant_1, cq:predisposition_1)) }""")),
            ("nonentail", "class level: no superclass of disease predisposition forces a realization (restriction on BFO_0000054 'has realization' or a sub-property)",
             forced_property_tbox("mild:MILD_120023", "obo:BFO_0000054")),
            ("nonentail", "class level: no superclass of disease predisposition forces a filler under disorder development process (MILD_120021)",
             forced_filler_tbox("mild:MILD_120023", "mild:MILD_120021")),
            ("nonentail", "class level: genetic variant (MILD_120009) is not a subclass of material disease entity (not every variant is pathological)",
             "ASK { mild:MILD_120009 rdfs:subClassOf* mild:MILD_120020 }"),
            ("probe", "predisposition and material disease entity cannot share an instance (probe class unsatisfiable)",
             PROBE_NS + "P_predisposition_and_disease"),
            ("entail", "realized branch: target_development_process_r is inferred to be a disorder development process (MILD_120021) and a process (BFO_0000015)",
             "ASK { cq:target_development_process_r a mild:MILD_120021 , obo:BFO_0000015 }"),
            ("entail", "realized branch: target_disorder_r is inferred to be a material disease entity",
             has_type("cq:target_disorder_r", "mild:MILD_120020")),
            ("nonentail", "realized branch: variant_1r and target_disorder_r are not inferred identical (the variant is not the target disease)",
             same_as("cq:variant_1r", "cq:target_disorder_r")),
        ],
    },
    {
        "id": "CQ4",
        "question": "Can a disease persist while its material constituents change?",
        "expected_answer": "yes",
        "how": "disease_4 has two successive constituents, disorder_state_t1 and disorder_state_t2, the second "
               "deriving from the first (RO_0001000), both asserted different. The ontology must keep disease_4 "
               "one material disease entity with both parts, must not identify the two states, and no axiom may "
               "close or fix the parts of a material disease entity. OWL has no time index, so this is what a "
               "reasoner can check of persistence.",
        "checks": [
            ("entail", "disease_4 is a material disease entity and inferred material entity (BFO_0000040) and independent continuant (BFO_0000004)",
             "ASK { cq:disease_4 a mild:MILD_120020 , obo:BFO_0000040 , obo:BFO_0000004 }"),
            ("entail", "both disorder states are inferred material disease entities and both are part of the one disease_4",
             textwrap.dedent("""\
                ASK { cq:disorder_state_t1 a mild:MILD_120020 ; obo:BFO_0000050 cq:disease_4 .
                      cq:disorder_state_t2 a mild:MILD_120020 ; obo:BFO_0000050 cq:disease_4 .
                      cq:disorder_state_t2 obo:RO_0001000 cq:disorder_state_t1 }""")),
            ("nonentail", "disorder_state_t1 and disorder_state_t2 are not inferred identical",
             same_as("cq:disorder_state_t1", "cq:disorder_state_t2")),
            ("nonentail", "disease_4 is not inferred identical with either constituent",
             "ASK { { cq:disease_4 owl:sameAs ?x } UNION { ?x owl:sameAs cq:disease_4 } FILTER(?x IN (cq:disorder_state_t1, cq:disorder_state_t2)) }"),
            ("nonentail", "class level: no superclass of material disease entity closes or caps 'has part' (only / max / exact cardinality)",
             upper_cardinality_tbox("mild:MILD_120020", "obo:BFO_0000051")),
        ],
    },
    {
        "id": "CQ5",
        "question": "Can a complication disorder be produced by disease A but grouped as disease B?",
        "expected_answer": "yes",
        "how": "complication_process_5 is a disorder creating disease course process, part of course_A5 (which has "
               "participant disease_A5) and has output disorder_B5. disorder_B5 is part of disease_B5, and "
               "diagnosis_B5 is about it. The reasoner must classify the process as both a disorder development "
               "process and a course of the disease process, classify disorder_B5 as a material disease entity, "
               "and must not make disorder_B5 a part of disease_A5 or identify the two diseases.",
        "checks": [
            ("entail", "complication_process_5 is inferred to be a disorder development process (MILD_120021), a course of the disease process (MILD_120028) and a process (BFO_0000015)",
             "ASK { cq:complication_process_5 a mild:MILD_120021 , mild:MILD_120028 , obo:BFO_0000015 }"),
            ("entail", "complication_process_5 is part of disease A's course and has output disorder_B5",
             "ASK { cq:complication_process_5 obo:BFO_0000050 cq:course_A5 ; obo:RO_0002234 cq:disorder_B5 }"),
            ("entail", "disorder_B5 is inferred to be a material disease entity and is grouped by diagnosis_B5 (is about) as part of disease_B5",
             "ASK { cq:disorder_B5 a mild:MILD_120020 ; obo:BFO_0000050 cq:disease_B5 . cq:diagnosis_B5 obo:IAO_0000136 cq:disorder_B5 }"),
            ("nonentail", "disease_A5 and disease_B5 are not inferred identical",
             same_as("cq:disease_A5", "cq:disease_B5")),
            ("nonentail", "disorder_B5 is not inferred to be part of disease_A5 (neither direction)",
             "ASK { { cq:disorder_B5 obo:BFO_0000050 cq:disease_A5 } UNION { cq:disease_A5 obo:BFO_0000051 cq:disorder_B5 } }"),
            ("nonentail", "disorder_B5 is not inferred to be a diagnostic result, and diagnosis_B5 not a material disease entity",
             "ASK { { cq:disorder_B5 a mild:MILD_120024 } UNION { cq:diagnosis_B5 a mild:MILD_120020 } }"),
        ],
    },
    {
        "id": "CQ6",
        "question": "Is a diagnostic category itself a disease?",
        "expected_answer": "no",
        "how": "The information entities of the test (diagnosis_A, diagnosis_B5, stage_result_6, threshold_6) must "
               "be inferred information content entities and generically dependent continuants, and must not be "
               "material disease entities or material entities. At class level no diagnostic result, classification "
               "result, threshold specification or DOID class may be a subclass of material disease entity. Probe "
               "classes show the first three can never share an instance with material disease entity. For DOID the "
               "test can only show the non-entailment: the DOID module gives DOID_4 no parent class.",
        "checks": [
            ("entail", "diagnosis_A, diagnosis_B5, stage_result_6 and threshold_6 are inferred information content entities (IAO_0000030) and generically dependent continuants (BFO_0000031)",
             textwrap.dedent("""\
                ASK { cq:diagnosis_A a obo:IAO_0000030 , obo:BFO_0000031 .
                      cq:diagnosis_B5 a obo:IAO_0000030 , obo:BFO_0000031 .
                      cq:stage_result_6 a obo:IAO_0000030 , obo:BFO_0000031 .
                      cq:threshold_6 a obo:IAO_0000030 , obo:BFO_0000031 }""")),
            ("nonentail", "none of the four information entities is inferred to be a material disease entity (MILD_120020) or a material entity (BFO_0000040)",
             textwrap.dedent("""\
                ASK { ?x a ?t . FILTER(?t IN (mild:MILD_120020, obo:BFO_0000040))
                      FILTER(?x IN (cq:diagnosis_A, cq:diagnosis_B5, cq:stage_result_6, cq:threshold_6)) }""")),
            ("nonentail", "class level: disease diagnostic result, disease stage classification result and disease threshold specification are not subclasses of material disease entity",
             textwrap.dedent("""\
                ASK { ?c rdfs:subClassOf* mild:MILD_120020 .
                      FILTER(?c IN (mild:MILD_120024, mild:MILD_120054, mild:MILD_120029)) }""")),
            ("nonentail", "class level: no DOID class is a subclass of material disease entity, and material disease entity is no subclass of any DOID class",
             textwrap.dedent(f"""\
                ASK {{ {{ ?c rdfs:subClassOf* mild:MILD_120020 }} UNION {{ mild:MILD_120020 rdfs:subClassOf* ?c }}
                      FILTER(STRSTARTS(STR(?c), "{OBO}DOID_")) }}""")),
            ("nonentail", "class level: material disease entity is not a subclass of information content entity",
             "ASK { mild:MILD_120020 rdfs:subClassOf* obo:IAO_0000030 }"),
            ("probe", "disease diagnostic result and material disease entity cannot share an instance",
             PROBE_NS + "P_diagnostic_result_and_disease"),
            ("probe", "disease stage classification result and material disease entity cannot share an instance",
             PROBE_NS + "P_stage_result_and_disease"),
            ("probe", "disease threshold specification and material disease entity cannot share an instance (follows from the BFO/IAO closure, not from an asserted disjointness)",
             PROBE_NS + "P_threshold_spec_and_disease"),
            ("probe", "information content entity and material disease entity cannot share an instance",
             PROBE_NS + "P_information_entity_and_disease"),
            ("probe-info", "DOID 'disease' (DOID_4) and material disease entity: informational, see the question's note",
             PROBE_NS + "P_doid_disease_and_disease"),
        ],
    },
]

GLOBAL_CHECKS = [
    ("nonentail", "no owl:sameAs between any two distinct individuals of the test data", ANY_SAMEAS_IN_TEST),
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def log(msg: str = "") -> None:
    print(msg, flush=True)


def find_current_mild(explicit: str | None) -> Path:
    if explicit:
        p = Path(explicit)
        if not p.is_absolute():
            p = (Path.cwd() / p).resolve()
        if not p.is_file():
            sys.exit(f"ERROR: --mild file not found: {p}")
        return p
    if not BUILD_SCRIPT.is_file():
        sys.exit(f"ERROR: build script not found, cannot determine current MILD file: {BUILD_SCRIPT}")
    text = BUILD_SCRIPT.read_text(encoding="utf-8")
    m = re.search(r'^INPUT="\$SCRIPT_DIR/([^"]+)"', text, re.M)
    if not m:
        sys.exit("ERROR: no INPUT=\"$SCRIPT_DIR/...\" line in build_disease_proposal.sh")
    p = DISEASE_DIR / m.group(1)
    if not p.is_file():
        sys.exit(f"ERROR: build script points at a MILD file that does not exist: {p}")
    return p


def file_uri(p: Path) -> str:
    return "file:" + quote(str(p.resolve()))


def write_catalog(work: Path, mild: Path) -> Path:
    entries = [(MILD_IRI, mild)]
    # Module IRIs: every module file present, so a module MILD imports is found.
    for f in sorted(MODULE_DIR.glob("*_module.owl")):
        entries.append((MODULE_NS + f.name, f))
    for iri, f in WHOLE_IMPORTS.items():
        if not f.is_file():
            sys.exit(f"ERROR: local copy for {iri} missing: {f}")
        entries.append((iri, f))
    lines = ['<?xml version="1.0" encoding="UTF-8" standalone="no"?>',
             '<catalog prefer="public" xmlns="urn:oasis:names:tc:entity:xmlns:xml:catalog">']
    for i, (iri, f) in enumerate(entries):
        lines.append(f'    <uri id="cq test {i}" name="{iri}" uri="{file_uri(f)}"/>')
    lines.append("</catalog>")
    cat = work / "catalog-v001.xml"
    cat.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return cat


def check_imports_resolvable(mild: Path, cat: Path) -> None:
    """Every owl:imports of the MILD file must have a catalog entry (no silent web fetch)."""
    g = rdflib.Graph().parse(str(mild), format="turtle")
    cat_text = cat.read_text(encoding="utf-8")
    missing = [str(o) for o in g.objects(None, rdflib.OWL.imports) if f'name="{o}"' not in cat_text]
    if missing:
        sys.exit("ERROR: MILD imports IRIs the test catalog does not map (add them to WHOLE_IMPORTS):\n  "
                 + "\n  ".join(missing))


def robot(args: list[str], log_file: Path) -> subprocess.CompletedProcess:
    if not Path(ROBOT_JAR).is_file():
        sys.exit(f"ERROR: ROBOT jar not found at {ROBOT_JAR}")
    cmd = ["java", *JAVA_OPTS, "-jar", ROBOT_JAR, *args]
    t0 = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True)
    log_file.write_text(f"$ {' '.join(cmd)}\n\n--- stdout ---\n{proc.stdout}\n--- stderr ---\n{proc.stderr}\n", encoding="utf-8")
    proc.seconds = time.time() - t0  # type: ignore[attr-defined]
    proc.log = proc.stdout + "\n" + proc.stderr  # ROBOT writes its log lines to stdout  # type: ignore[attr-defined]
    return proc


UNSAT_RE = re.compile(r"unsatisfiable:\s*(\S+)")


def parse_unsatisfiable(stderr: str) -> set[str]:
    return {m.group(1).strip("<>") for m in UNSAT_RE.finditer(stderr)}


def label_of(g: rdflib.Graph, iri: str) -> str:
    l = g.value(rdflib.URIRef(iri), rdflib.RDFS.label)
    return str(l) if l else iri.split("/")[-1]


# ---------------------------------------------------------------------------
# Query dump
# ---------------------------------------------------------------------------

def dump_queries(path: Path, mild: Path, reasoner: str) -> None:
    out = []
    out.append("# MILD competency questions: the queries that decide the test\n")
    out.append(f"Generated by `tests/run_mild_cq_tests.py --dump-queries` on {time.strftime('%Y-%m-%d')} "
               f"for MILD file `{mild.name}`; default reasoner {reasoner}.\n")
    out.append("The runner merges `tests/mild_cq_test_2026-10-30.ttl` (named individuals) with the full MILD import "
               "closure, reasons it with ROBOT (ELK by default, HermiT with `--reasoner HermiT`), writes the inferred "
               "class assertions into the output and runs every query below as a SPARQL ASK over that output. "
               "An *expected entailment* must come back true, an *expected non-entailment* false. *Probe classes* "
               "(in `tests/mild_cq_probes_2026-10-30.ttl`) are reasoned in a second run and must be reported "
               "unsatisfiable. A question passes only if every one of its checks passes; a query that errors fails "
               "its question.\n")
    out.append("Prefixes used in every query:\n")
    out.append("```sparql\n" + PREFIXES + "```\n")
    for cq in CQS:
        out.append(f"## {cq['id']}. {cq['question']}\n")
        out.append(f"Expected answer: **{cq['expected_answer']}**.\n")
        out.append(cq["how"] + "\n")
        for kind, desc, q in cq["checks"]:
            if kind == "entail":
                out.append(f"**Expected entailment (ASK must be true):** {desc}\n\n```sparql\n{q}\n```\n")
            elif kind == "nonentail":
                out.append(f"**Expected non-entailment (ASK must be false):** {desc}\n\n```sparql\n{q}\n```\n")
            elif kind == "probe":
                out.append(f"**Probe class (must be unsatisfiable):** {desc}\n\n`{q}`\n")
            else:
                out.append(f"**Informational probe (reported, does not decide):** {desc}\n\n`{q}`\n")
    out.append("## Whole test data\n")
    for kind, desc, q in GLOBAL_CHECKS:
        out.append(f"**Expected non-entailment (ASK must be false):** {desc}\n\n```sparql\n{q}\n```\n")
    out.append("## What the reasoner cannot decide\n")
    out.append("ELK implements OWL 2 EL: it ignores inverse-property axioms, `owl:differentFrom` and inverse-functional "
               "properties, and it never derives `owl:sameAs`. Under ELK the \"not identical\" checks therefore show "
               "that nothing in the axioms *could* force an identity (no functional or inverse-functional property, "
               "no cardinality cap) and that the reasoned output holds no `owl:sameAs`. Under HermiT the asserted "
               "`owl:differentFrom` pairs make a forced identity an inconsistency, so the main run would fail.\n")
    out.append("OWL has no time index. CQ4 is checked as far as a reasoner can: one individual keeps two successive "
               "constituents, they are not identified, and no axiom closes or fixes the parts of a material disease entity.\n")
    path.write_text("\n".join(out), encoding="utf-8")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reasoner", default="ELK", choices=["ELK", "HermiT", "hermit", "elk"],
                    help="ELK (default, about a minute) or HermiT (hours on the full closure)")
    ap.add_argument("--mild", help="MILD .ttl to test (default: INPUT= of build_disease_proposal.sh)")
    ap.add_argument("--work-dir", help="keep merged/reasoned files here (default: temporary dir, deleted)")
    ap.add_argument("--dump-queries", metavar="MD", help="also write the query list as Markdown to this path")
    ap.add_argument("--skip-probes", action="store_true", help="do not run the probe run (probe checks then FAIL, never skip silently)")
    args = ap.parse_args()
    reasoner = "HermiT" if args.reasoner.lower() == "hermit" else "ELK"

    mild = find_current_mild(args.mild)
    for f in (TEST_TTL, PROBE_TTL):
        if not f.is_file():
            sys.exit(f"ERROR: missing {f}")

    if args.work_dir:
        work = Path(args.work_dir).resolve(); work.mkdir(parents=True, exist_ok=True); cleanup = False
    else:
        work = Path(tempfile.mkdtemp(prefix="mild_cq_")); cleanup = True

    log(f"MILD file      : {mild}")
    log(f"test data      : {TEST_TTL.name}")
    log(f"probe classes  : {PROBE_TTL.name}")
    log(f"reasoner       : {reasoner}")
    log(f"work dir       : {work}{' (temporary)' if cleanup else ''}")

    if args.dump_queries:
        dump_queries(Path(args.dump_queries), mild, reasoner)
        log(f"queries written: {args.dump_queries}")

    cat = write_catalog(work, mild)
    check_imports_resolvable(mild, cat)

    # 1. merge ---------------------------------------------------------------
    merged = work / "cq_merged.owl"
    log("\n[1/4] ROBOT merge: test data + MILD import closure ...")
    p = robot(["merge", "--catalog", str(cat), "--input", str(TEST_TTL), "--output", str(merged)], work / "merge.log")
    if p.returncode != 0 or not merged.is_file():
        log(p.log[-3000:]); return fail_all("ROBOT merge failed")
    log(f"      merged in {p.seconds:.0f}s -> {merged.stat().st_size/1e6:.1f} MB")
    # sanity: the closure really is in there (no silent half-merge)
    gm = rdflib.Graph().parse(str(merged))
    for iri, what in ((MILD_NS + "MILD_120020", "material disease entity"), (OBO + "RO_0000086", "has quality (RO)"),
                      (OBO + "BFO_0000040", "material entity (BFO)"), (OBO + "IAO_0000030", "information content entity (IAO)"),
                      (OBO + "NCBITaxon_9606", "Homo sapiens (module)"), (OBO + "DOID_4", "disease (DOID module)")):
        if (rdflib.URIRef(iri), rdflib.RDFS.label, None) not in gm:
            return fail_all(f"merged closure lacks a label for {what} <{iri}>: an import did not resolve")
    log(f"      closure check ok: {len(gm):,} triples, MILD + BFO + RO + IAO + modules present")
    del gm

    # 2. reason (main) --------------------------------------------------------
    reasoned = work / "cq_reasoned.ttl"
    log(f"\n[2/4] ROBOT reason ({reasoner}), main run: must be consistent with no unsatisfiable class ...")
    p = robot(["reason", "--reasoner", reasoner, "--input", str(merged),
               "--axiom-generators", "SubClass ClassAssertion PropertyAssertion",
               "--include-indirect", "true", "--output", str(reasoned)], work / "reason_main.log")
    if p.returncode != 0 or not reasoned.is_file():
        unsat = parse_unsatisfiable(p.log)
        reason = "ontology INCONSISTENT" if "inconsistent" in p.log.lower() else "reasoning failed"
        if unsat:
            reason = f"{len(unsat)} unsatisfiable class(es): " + ", ".join(sorted(unsat))
        log(p.log[-3000:]); return fail_all(f"main reasoning run: {reason}")
    warn = [l for l in p.log.splitlines() if "WARN" in l]
    log(f"      reasoned in {p.seconds:.0f}s, consistent, no unsatisfiable class; {len(warn)} reasoner warnings (see reason_main.log)")

    # 3. reason (probes) ------------------------------------------------------
    log(f"\n[3/4] ROBOT reason ({reasoner}), probe run: probe classes must come back unsatisfiable ...")
    unsat: set[str] | None = None
    probe_note = ""
    if args.skip_probes:
        probe_note = "probe run skipped by --skip-probes"
    else:
        merged_p = work / "cq_merged_probes.owl"
        p = robot(["merge", "--catalog", str(cat), "--input", str(TEST_TTL), "--input", str(PROBE_TTL),
                   "--output", str(merged_p)], work / "merge_probes.log")
        if p.returncode != 0:
            log(p.log[-3000:]); return fail_all("ROBOT merge of probe run failed")
        p = robot(["reason", "--reasoner", reasoner, "--input", str(merged_p),
                   "--dump-unsatisfiable", str(work / "cq_unsatisfiable.owl"),
                   "--output", str(work / "cq_reasoned_probes.ttl")], work / "reason_probes.log")
        if "inconsistent" in p.log.lower():
            probe_note = "probe run: ontology INCONSISTENT (a probe class has an instance?)"
            unsat = set()
        elif p.returncode == 0:
            unsat = set()
            probe_note = "probe run succeeded: NO class unsatisfiable"
        else:
            unsat = parse_unsatisfiable(p.log)
            if not unsat:
                log(p.log[-3000:]); return fail_all("probe reasoning failed for another reason than unsatisfiable classes")
        log(f"      probe run in {p.seconds:.0f}s: {len(unsat)} unsatisfiable class(es)" + (f"; {probe_note}" if probe_note else ""))
        expected_probes = {q for cq in CQS for k, _, q in cq["checks"] if k in ("probe", "probe-info")}
        stray = unsat - expected_probes
        if stray:
            log("      UNEXPECTED unsatisfiable classes outside the probes:\n        " + "\n        ".join(sorted(stray)))

    # 4. SPARQL checks --------------------------------------------------------
    log(f"\n[4/4] SPARQL ASK checks over {reasoned.name} ...")
    g = rdflib.Graph().parse(str(reasoned), format="turtle")
    log(f"      {len(g):,} triples loaded\n")

    def ask(q: str) -> bool:
        res = g.query(PREFIXES + q)
        return bool(res.askAnswer)

    all_ok = True
    results = []
    for cq in CQS:
        log(f"{'='*78}\n{cq['id']}  {cq['question']}   (expected: {cq['expected_answer']})\n{'-'*78}")
        ok = True
        for kind, desc, q in cq["checks"]:
            try:
                if kind in ("entail", "nonentail"):
                    got = ask(q)
                    want = kind == "entail"
                    good = got == want
                    tag = "ok " if good else "XX "
                    log(f"  [{tag}] {'entailment    ' if want else 'non-entailment'}: {desc}")
                    log(textwrap.indent(q.strip(), "          "))
                    log(f"          -> ASK = {str(got).lower()}  (expected {str(want).lower()})")
                elif kind == "probe":
                    if unsat is None:
                        good = False; verdict = "NOT RUN (" + probe_note + ")"
                    else:
                        good = q in unsat; verdict = "unsatisfiable" if good else "SATISFIABLE"
                    tag = "ok " if good else "XX "
                    log(f"  [{tag}] probe class   : {desc}\n          {q}\n          -> {verdict}  (expected unsatisfiable)")
                else:  # probe-info
                    good = True
                    verdict = "not run" if unsat is None else ("unsatisfiable" if q in unsat else "SATISFIABLE")
                    log(f"  [i  ] informational : {desc}\n          {q}\n          -> {verdict}  (does not decide {cq['id']})")
                    if unsat is not None and q not in unsat:
                        log("          note: MILD cannot exclude an instance here; the DOID module carries no parent class for DOID_4.")
            except Exception:
                good = False
                log(f"  [XX ] ERROR while evaluating: {desc}\n" + textwrap.indent(traceback.format_exc(), "          "))
            ok = ok and good
        results.append((cq["id"], ok))
        all_ok = all_ok and ok
        log(f"\n{cq['id']}: {'PASS' if ok else 'FAIL'}\n")

    log(f"{'='*78}\nWhole test data\n{'-'*78}")
    for kind, desc, q in GLOBAL_CHECKS:
        try:
            got = ask(q); good = got is False
        except Exception:
            good = False; got = "ERROR"; log(textwrap.indent(traceback.format_exc(), "          "))
        log(f"  [{'ok ' if good else 'XX '}] non-entailment: {desc}\n{textwrap.indent(q.strip(), '          ')}\n          -> ASK = {str(got).lower()}  (expected false)")
        all_ok = all_ok and good
    if unsat is not None and (unsat - {q for cq in CQS for k, _, q in cq["checks"] if k in ("probe", "probe-info")}):
        log("  [XX ] unexpected unsatisfiable classes in the probe run (listed above)")
        all_ok = False

    log(f"\n{'='*78}\nSUMMARY  (MILD {mild.name}, reasoner {reasoner})\n{'-'*78}")
    for cid, ok in results:
        log(f"  {cid}: {'PASS' if ok else 'FAIL'}")
    log(f"  overall: {'PASS' if all_ok else 'FAIL'}")
    if cleanup:
        shutil.rmtree(work, ignore_errors=True)
    else:
        log(f"  files kept in {work}")
    return 0 if all_ok else 1


def fail_all(reason: str) -> int:
    log(f"\nRUN FAILED before the per-question checks: {reason}")
    for cq in CQS:
        log(f"  {cq['id']}: FAIL ({reason})")
    log("  overall: FAIL")
    return 1


if __name__ == "__main__":
    sys.exit(main())
